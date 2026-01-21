import streamlit as st
from groq import Groq
from docx import Document
from io import BytesIO
from datetime import datetime, timedelta
import json
import base64
import time
import re
import os

# Dependências opcionais
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except Exception:
    PDFPLUMBER_AVAILABLE = False

try:
    import docx as docx_reader
    DOCX_READER_AVAILABLE = True
except Exception:
    DOCX_READER_AVAILABLE = False

try:
    from PIL import Image, ImageFilter, ImageOps
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# =============================================================================
# 1. Configuração e design
# =============================================================================
st.set_page_config(page_title="Carmélio AI | Suíte Jurídica Pro", page_icon="logo.jpg.png", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    .question-card { background-color: #1F2430; padding: 20px; border-radius: 12px; border-left: 5px solid #3B82F6; margin-bottom: 15px; }
    .flashcard { background: linear-gradient(135deg, #1F2430 0%, #282C34 100%); padding: 24px; border-radius: 12px; border: 1px solid #3B82F6; text-align: center; }
    .xp-badge { background-color: #FFD700; color: #000; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 12px; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #161922; border: 1px solid #2B2F3B; color: #E0E7FF; border-radius: 8px;
    }
    .stButton>button {
        width: 100%; border-radius: 8px; height: 45px; font-weight: 600; border: none;
        background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%);
        color: white; transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4); color: white;}
    h1, h2, h3 { color: #F3F4F6; font-family: 'Inter', sans-serif; }
    p, label, .stMarkdown { color: #9CA3AF; }
    .profile-box { text-align: center; margin-bottom: 20px; color: #E0E7FF; }
    .profile-name { font-weight: bold; font-size: 18px; margin-top: 5px; color: #FFFFFF; }
    .profile-role { font-size: 12px; color: #3B82F6; text-transform: uppercase; letter-spacing: 1px; }
    .timer-display { font-size: 72px; font-weight: bold; color: #FFFFFF; text-align: center; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. Estado, gamificação, LGPD e rate limiting
# =============================================================================
if "user_xp" not in st.session_state: st.session_state.user_xp = 0
if "user_level" not in st.session_state: st.session_state.user_level = 1
if "edital_text" not in st.session_state: st.session_state.edital_text = ""
if "edital_topics" not in st.session_state: st.session_state.edital_topics = []
if "generated_questions" not in st.session_state: st.session_state.generated_questions = []
if "question_stats" not in st.session_state: st.session_state.question_stats = {}
if "cards" not in st.session_state: st.session_state.cards = []
if "logs" not in st.session_state: st.session_state.logs = []
if "lgpd_ack" not in st.session_state: st.session_state.lgpd_ack = False
if "last_heavy_call" not in st.session_state: st.session_state.last_heavy_call = 0.0

RATE_LIMIT_SECONDS = 15

def add_xp(amount):
    st.session_state.user_xp += amount
    new_level = (st.session_state.user_xp // 100) + 1
    if new_level > st.session_state.user_level:
        st.toast(f"🎉 PARABÉNS! Você subiu para o Nível {new_level}!", icon="🆙")
        st.session_state.user_level = new_level
    else:
        st.toast(f"+{amount} XP ganho!", icon="⭐")

def rate_limited():
    now = time.time()
    if now - st.session_state.last_heavy_call < RATE_LIMIT_SECONDS:
        return True, RATE_LIMIT_SECONDS - (now - st.session_state.last_heavy_call)
    return False, 0

def mark_heavy_call():
    st.session_state.last_heavy_call = time.time()

def add_log(task_type, model, latency_ms, token_usage, status):
    st.session_state.logs.append({
        "task_type": task_type,
        "model": model,
        "latency_ms": latency_ms,
        "token_usage": token_usage,
        "status": status,
        "timestamp": datetime.now().isoformat()
    })

# LGPD
if not st.session_state.lgpd_ack:
    with st.expander("🔐 LGPD e Tratamento de Dados (Clique para ler)", expanded=True):
        st.markdown("""
        **Termos de Uso do Carmélio AI:**
        - Este sistema utiliza Inteligência Artificial para processar textos, imagens e áudios.
        - Seus dados são processados pela Groq API e não são retidos permanentemente.
        - Ao continuar, você concorda com o processamento para fins de estudo e produtividade.
        """)
        if st.button("Concordo e quero entrar"):
            st.session_state.lgpd_ack = True
            st.rerun()
    st.stop()

# =============================================================================
# 3. Backend (Groq)
# =============================================================================
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return None, "⚠️ Configure a GROQ_API_KEY nos Secrets."
    return Groq(api_key=api_key), None

def criar_docx(texto, titulo="Documento Carmélio AI"):
    try:
        doc = Document()
        doc.add_heading(titulo, 0)
        for p in str(texto).split('\n'):
            if p.strip(): doc.add_paragraph(p)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception:
        return None

def processar_ia(prompt, file_bytes=None, task_type="text", system_instruction="Você é um assistente útil.", model_override=None, temperature=0.3):
    client, erro = get_groq_client()
    if erro: return f"Erro de Configuração: {erro}"
    start = time.time()
    try:
        if task_type == "vision":
            model = "llama-3.2-11b-vision-preview"
        elif task_type == "audio":
            model = "whisper-large-v3"
        else:
            model = model_override if model_override else "llama-3.3-70b-versatile"

        if task_type == "vision" and file_bytes:
            b64 = base64.b64encode(file_bytes).decode('utf-8')
            content = client.chat.completions.create(
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt},{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
                model=model, temperature=0.1
            ).choices[0].message.content
            add_log("vision", model, int((time.time()-start)*1000), len(prompt), "ok")
            return content

        elif task_type == "audio" and file_bytes:
            import tempfile
            suffix = ".mp3"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes); tmp_path = tmp.name
            with open(tmp_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), file.read()),
                    model=model, response_format="text", language="pt"
                )
            os.unlink(tmp_path)
            add_log("audio", model, int((time.time()-start)*1000), len(file_bytes), "ok")
            return transcription

        else:
            content = client.chat.completions.create(
                messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}],
                model=model, temperature=temperature
            ).choices[0].message.content
            add_log("text", model, int((time.time()-start)*1000), len(prompt), "ok")
            return content

    except Exception as e:
        add_log(task_type, model_override or "auto", int((time.time()-start)*1000), len(prompt) if prompt else 0, f"error: {e}")
        return f"❌ Erro na IA: {str(e)}"

# =============================================================================
# 4. Utilitários de validação e extração
# =============================================================================
def validate_json_response(response_text):
    try:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
            required = ["enunciado", "alternativas", "gabarito", "comentario"]
            if all(key in data for key in required):
                return data
    except:
        pass
    return None

def validate_question_json(data):
    try:
        assert set(data.keys()) == {"enunciado", "alternativas", "gabarito", "comentario"}
        assert all(k in data["alternativas"] for k in ["A", "B", "C", "D", "E"])
        assert data["gabarito"] in ["A", "B", "C", "D", "E"]
        assert data["alternativas"][data["gabarito"]].strip() != ""
        has_citation = any(tag in data["comentario"] for tag in ["art.", "Lei", "Súmula", "Tema", "STF", "STJ"])
        assert has_citation
        return True, ""
    except AssertionError:
        return False, "Formato inválido ou sem citações mínimas."

def extract_json_from_text(text):
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None

# =============================================================================
# 5. Sidebar
# =============================================================================
with st.sidebar:
    try:
        st.image("logo.jpg.png", use_container_width=True)
    except:
        st.warning("⚠️ Logo não encontrada.")
    st.markdown("""
    <div class="profile-box">
        <small>Desenvolvido por</small><br>
        <div class="profile-name">Arthur Carmélio</div>
        <div class="profile-role">ESPECIALISTA NOTARIAL</div>
    </div>
    """, unsafe_allow_html=True)

    c_lvl, c_xp = st.columns(2)
    c_lvl.metric("Nível", st.session_state.user_level)
    c_xp.metric("XP", st.session_state.user_xp)
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))

    st.markdown("---")
    menu_opcao = st.radio("Menu Principal:",
        ["🎓 Área do Estudante", "💬 Mentor Jurídico", "📄 Redação de Contratos", "🏢 Cartório Digital (OCR)", "🎙️ Transcrição", "⭐ Feedback", "📊 Logs", "👤 Sobre"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    col_link, col_zap = st.columns(2)
    with col_link:
        st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")
    with col_zap:
        st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720?text=Suporte%20Carmelio%20AI)")

# =============================================================================
# 6. Listas globais (jurídico, policial, auditoria) + bancas + UFs
# =============================================================================
DISCIPLINAS = [
    # Jurídico
    "Direito Constitucional", "Direito Administrativo", "Direito Penal", "Direito Civil",
    "Processo Penal", "Processo Civil", "Direito Tributário", "Direito do Trabalho",
    "Processo do Trabalho", "Direito Empresarial", "Direitos Humanos", "Direito Ambiental",
    "Direito Internacional", "Notarial e Registral", "Ética Profissional", "Português",
    "RLM", "Informática",
    # Policial
    "Direito Penal Militar", "Processo Penal Militar", "Criminologia", "Legislação Penal Especial",
    "Investigação Criminal", "Segurança Pública", "Inteligência Policial",
    "Direitos Humanos aplicados à Segurança",
    # Auditoria/Controle
    "Contabilidade Geral", "Contabilidade Pública", "Auditoria Governamental",
    "Administração Pública", "Controle Interno", "Finanças Públicas",
    "Direito Financeiro", "Gestão de Riscos", "Normas de Auditoria"
]

BANCAS = [
    "FGV", "Cebraspe", "Vunesp", "FCC", "AOCP", "Comperve", "IBFC", "Quadrix",
    "Cesgranrio", "Idecan", "Iades", "Funrio", "Fundatec", "Fepese", "Instituto Consulplan"
]

UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO", "Federal"
]

# =============================================================================
# 7. Módulos
# =============================================================================

# --- ESTUDANTE PRO ---
if menu_opcao == "🎓 Área do Estudante":
    st.title("🎓 Área do Estudante Pro")
    tab_questoes, tab_edital, tab_flash, tab_crono = st.tabs(["📝 Banco Infinito", "🎯 Mestre dos Editais", "⚡ Flashcards", "📅 Cronograma"])

    # 1.1 QUESTÕES
    with tab_questoes:
        st.markdown("### 🔎 Gerador de Questões Inéditas")
        c1, c2, c3, c4 = st.columns(4)
        disc = c1.selectbox("Disciplina", DISCIPLINAS)
        banca = c2.selectbox("Banca", BANCAS)
        uf = c3.selectbox("UF/Tribunal", UFS)
        nivel = c4.selectbox("Nível", ["Fácil", "Médio", "Difícil"])
        assunto = st.text_input("Assunto", placeholder="Ex: Atos Administrativos")
        cargo = st.text_input("Cargo", placeholder="Ex: Escrevente")

        if st.button("Gerar Questão"):
            with st.spinner("Elaborando questão..."):
                nivel_instr = {
                    "Fácil": "Use linguagem simples, conceito básico e alternativa correta evidente.",
                    "Médio": "Exija interpretação e aplicação prática moderada, com alternativas plausíveis.",
                    "Difícil": "Inclua nuances, jurisprudência e pegadinhas típicas da banca."
                }[nivel]
                prompt = (
                    "Gere 1 questão inédita em JSON com campos: enunciado, alternativas (A,B,C,D,E), gabarito (A–E), comentario. "
                    f"Disciplina: {disc}. Assunto: {assunto}. Banca: {banca}. Cargo: {cargo}. Jurisdição: {uf}. "
                    f"Nível: {nivel}. {nivel_instr} "
                    "Cite artigos, súmulas ou precedentes (STF/STJ). Retorne APENAS JSON."
                )
                res = processar_ia(prompt, task_type="text", temperature=0.2)
                data = validate_json_response(res)
                if data:
                    ok, msg = validate_question_json(data)
                    if ok:
                        st.session_state.q_atual = data
                        st.session_state.ver_resp = False
                        st.session_state.question_stats.setdefault(disc, {"count": 0, "sim_acertos": 0})
                        st.session_state.question_stats[disc]["count"] += 1
                        add_xp(10)
                    else:
                        st.error(f"Erro validação: {msg}")
                else:
                    st.error("Erro na geração. Tente novamente.")

        if 'q_atual' in st.session_state:
            q = st.session_state.q_atual
            st.markdown(f"<div class='question-card'><h4>{disc} | {banca} | {uf} | {nivel}</h4><p>{q['enunciado']}</p></div>", unsafe_allow_html=True)
            for k in ["A","B","C","D","E"]: st.write(f"**{k})** {q['alternativas'].get(k, '')}")
            if st.button("👁️ Ver Gabarito"): st.session_state.ver_resp = True
            if st.session_state.get('ver_resp'):
                st.success(f"Gabarito: {q['gabarito']}")
                st.info(f"Comentário: {q['comentario']}")
                st.session_state.generated_questions.append(q)
                if criar_docx(json.dumps(q, ensure_ascii=False, indent=2), "Questão"):
                    st.download_button("💾 Baixar DOCX", criar_docx(json.dumps(q, ensure_ascii=False, indent=2), "Questão"), "Questao.docx")

        st.markdown("---")
        st.markdown("### 📦 Histórico e estatísticas")
        if st.session_state.generated_questions:
            st.write(f"Total: {len(st.session_state.generated_questions)} questões")
            for disc_name, stats in st.session_state.question_stats.items():
                st.write(f"- {disc_name}: {stats['count']} geradas")
            if criar_docx(json.dumps(st.session_state.generated_questions, ensure_ascii=False, indent=2), "Histórico de Questões"):
                st.download_button("💾 Baixar histórico (DOCX)", criar_docx(json.dumps(st.session_state.generated_questions, ensure_ascii=False, indent=2), "Histórico de Questões"), "Questoes_Historico.docx")
        else:
            st.info("Nenhuma questão gerada ainda.")

    # 1.2 MESTRE DOS EDITAIS
    with tab_edital:
        st.markdown("### 🎯 Verticalizador de Editais")
        col_up, col_txt = st.columns(2)
        with col_up:
            file = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf", "docx", "txt"])
        with col_txt:
            texto_manual = st.text_area("Ou cole o texto aqui:", height=150)

        def extract_text_from_pdf(file_bytes):
            if not PDFPLUMBER_AVAILABLE:
                return None, "pdfplumber não instalado."
            try:
                text = ""
                with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                return text, None
            except Exception as e:
                return None, f"Erro ao ler PDF: {e}"

        def extract_text_from_docx(file_bytes):
            if not DOCX_READER_AVAILABLE:
                return None, "python-docx não instalado."
            try:
                f = BytesIO(file_bytes)
                doc = docx_reader.Document(f)
                text = "\n".join([p.text for p in doc.paragraphs])
                return text, None
            except Exception as e:
                return None, f"Erro ao ler DOCX: {e}"

        def verticalize_edital(text):
            prompt = (
                "Extraia e liste os tópicos do edital abaixo, organizando por matéria e subtemas. "
                "Retorne em JSON com campos: 'materia', 'topicos' (lista de strings). "
                "Edital:\n" + text
            )
            r = processar_ia(prompt, task_type="text", system_instruction="Estruture em JSON válido.", temperature=0.1)
            data = extract_json_from_text(r)
            if not data:
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                materias = {}
                current = "Geral"
                for ln in lines:
                    if ln.isupper() and len(ln) > 3:
                        current = ln
                        materias[current] = []
                    else:
                        materias.setdefault(current, []).append(ln)
                return [{"materia": m, "topicos": t} for m, t in materias.items()]
            if isinstance(data, dict) and "materias" in data and isinstance(data["materias"], list):
                return data["materias"]
            if isinstance(data, list):
                return data
            return [{"materia": "Geral", "topicos": [text[:200] + "..."]}]

        if st.button("📊 Verticalizar Edital"):
            text_to_process = ""
            err = None
            if file:
                if file.type == "application/pdf":
                    text_to_process, err = extract_text_from_pdf(file.getvalue())
                    if not text_to_process or len(text_to_process.strip()) < 50:
                        st.info("PDF pode estar escaneado. Tentando OCR via IA...")
                        text_to_process = processar_ia("Transcreva fielmente este PDF escaneado.", file_bytes=file.getvalue(), task_type="vision")
                elif "word" in file.type or file.type == "application/octet-stream":
                    text_to_process, err = extract_text_from_docx(file.getvalue())
                else:
                    try:
                        text_to_process = file.getvalue().decode("utf-8", errors="ignore")
                    except Exception as e:
                        err = f"Erro ao ler TXT: {e}"
            elif texto_manual:
                text_to_process = texto_manual

            if err:
                st.error(err)
            elif len(text_to_process) > 50:
                st.session_state.edital_text = text_to_process
                with st.spinner("Analisando edital..."):
                    topics = verticalize_edital(text_to_process)
                    st.session_state.edital_topics = topics
                    st.success(f"Tópicos extraídos: {len(topics)} matérias.")
                    for item in topics[:10]:
                        st.markdown(f"- **{item['materia']}**: {min(len(item['topicos']), 5)} tópicos")
                    if criar_docx(json.dumps(topics, ensure_ascii=False, indent=2), "Edital Verticalizado"):
                        st.download_button("💾 Baixar tópicos (DOCX)", criar_docx(json.dumps(topics, ensure_ascii=False, indent=2), "Edital Verticalizado"), "Edital_Verticalizado.docx")
                    add_xp(20)
            else:
                st.warning("Texto muito curto ou inválido.")

        st.markdown("---")
        st.markdown("### 🧪 Treinamento por tópico")
        if st.session_state.edital_topics:
            materias = [t["materia"] for t in st.session_state.edital_topics]
            sel_materia = st.selectbox("Matéria", materias)
            sel_topicos = []
            for t in st.session_state.edital_topics:
                if t["materia"] == sel_materia:
                    sel_topicos = t["topicos"]
                    break
            topico = st.selectbox("Tópico", sel_topicos if sel_topicos else ["—"])
            c1, c2, c3, c4 = st.columns(4)
            banca_t = c1.selectbox("Banca", BANCAS)
            uf_t = c2.selectbox("UF/Tribunal", UFS)
            cargo_t = c3.text_input("Cargo", "Analista")
            nivel_t = c4.selectbox("Nível", ["Fácil", "Médio", "Difícil"])
            if st.button("Gerar questão do tópico"):
                prompt = (
                    "Gere 1 questão inédita em JSON com campos: enunciado, alternativas (A,B,C,D,E), gabarito, comentario. "
                    f"Matéria: {sel_materia}. Tópico: {topico}. Banca: {banca_t}. UF: {uf_t}. Cargo: {cargo_t}. Nível: {nivel_t}. "
                    "Cite artigos/súmulas/precedentes. Retorne APENAS JSON."
                )
                r = processar_ia(prompt, task_type="text", temperature=0.2)
                data = validate_json_response(r)
                if data:
                    ok, msg = validate_question_json(data)
                    if ok:
                        st.success("Questão gerada.")
                        st.json(data)
                        st.session_state.generated_questions.append(data)
                        add_xp(15)
                    else:
                        st.error(f"Validação falhou: {msg}")
                else:
                    st.error("Falha ao gerar JSON válido.")

    # 1.3 FLASHCARDS
    with tab_flash:
        st.markdown("### ⚡ Flashcards & Repetição espaçada")
        deck_disc = st.selectbox("Deck (Disciplina)", DISCIPLINAS)
        tema = st.text_input("Tema para memorizar")
        if st.button("Criar Flashcard"):
            r = processar_ia(f"Crie um flashcard sobre {tema}. Retorne: PERGUNTA --- RESPOSTA")
            if "---" in r:
                f, b = r.split("---")
                card = {"deck": deck_disc, "front": f.strip(), "back": b.strip(), "ease": 2.5, "interval": 1, "due": datetime.today().strftime("%Y-%m-%d")}
                st.session_state.cards.append(card)
                st.success("Criado!")
                add_xp(5)
            else:
                st.error("Erro formato.")

        st.markdown("#### Próximas revisões")
        today = datetime.today().strftime("%Y-%m-%d")
        due_cards = [c for c in st.session_state.cards if c["due"] <= today]
        if due_cards:
            for i, c in enumerate(due_cards[:10]):
                st.write(f"- [{c['deck']}] {c['front']}")
                fb = st.radio(f"Como foi? (Card {i+1})", ["Errei", "Duvidei", "Acertei"], horizontal=True, key=f"fb_{i}")
                if st.button(f"Registrar (Card {i+1})"):
                    if fb == "Errei":
                        c["ease"] = max(1.3, c["ease"] - 0.2)
                        c["interval"] = 1
                    elif fb == "Duvidei":
                        c["ease"] = max(1.3, c["ease"] - 0.1)
                        c["interval"] = max(1, int(c["interval"] * 1.2))
                    else:
                        c["ease"] = min(3.0, c["ease"] + 0.1)
                        c["interval"] = max(1, int(c["interval"] * c["ease"]))
                    next_due = datetime.today() + timedelta(days=c["interval"])
                    c["due"] = next_due.strftime("%Y-%m-%d")
                    st.success(f"Próxima revisão em {c['interval']} dias ({c['due']}).")

        if st.session_state.cards:
            csv = "deck,front,back\n" + "\n".join([f"{c['deck']},{c['front']},{c['back']}" for c in st.session_state.cards])
            st.download_button("💾 Baixar Anki CSV", csv, "anki.csv")

    # 1.4 CRONOGRAMA
    with tab_crono:
        st.markdown("### 📅 Cronograma com revisões")
        h = st.slider("Horas/dia", 1, 8, 4)
        topicos = st.text_area("Listar tópicos (um por linha)")
        if st.button("Gerar Plano"):
            topics = [t for t in topicos.split('\n') if t.strip()]
            plan = []
            base = datetime.today()
            for i, t in enumerate(topics):
                d = base + timedelta(days=i)
                rev1 = d + timedelta(days=1)
                rev2 = d + timedelta(days=7)
                plan.append(f"{d.strftime('%d/%m')} - {t} ({h}h) | Revisões: {rev1.strftime('%d/%m')}, {rev2.strftime('%d/%m')}")
            res = "\n".join(plan)
            st.text_area("Resultado", res, height=300)
            if criar_docx(res): st.download_button("💾 Baixar Plano", criar_docx(res), "Plano.docx")
            add_xp(15)

# --- MENTOR ---
elif menu_opcao == "💬 Mentor Jurídico":
    st.title("💬 Mentor Jurídico")
    perfil = st.selectbox("Perfil", ["Professor Didático", "Doutrinador (Técnico)", "Jurisprudencial", "Coach Motivacional"])
    if "chat" not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat: st.chat_message(m["role"]).write(m["content"])

    if p := st.chat_input("Dúvida..."):
        st.session_state.chat.append({"role":"user", "content":p})
        st.chat_message("user").write(p)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                sys = {
                    "Professor Didático": "Explique com exemplos e analogias, cite leis quando necessário.",
                    "Doutrinador (Técnico)": "Seja técnico, cite doutrina e artigos de lei.",
                    "Jurisprudencial": "Baseie-se em precedentes STF/STJ e súmulas.",
                    "Coach Motivacional": "Traga foco, disciplina e estratégia de estudo, sem prometer resultados."
                }[perfil]
                r = processar_ia(p, system_instruction=sys)
                st.write(r)
                st.session_state.chat.append({"role":"assistant", "content":r})
                add_xp(5)

    st.markdown("---")
    st.markdown("### ✅ Checklist jurídico automático")
    caso = st.text_area("Descreva o caso (fatos, partes, pedidos)")
    if st.button("Gerar checklist de riscos"):
        prompt = f"Com base no caso, gere um checklist de riscos jurídicos, pontos de atenção e documentos necessários. Caso: {caso}"
        r = processar_ia(prompt, task_type="text", temperature=0.2)
        st.write(r)

# --- CONTRATOS ---
elif menu_opcao == "📄 Redação de Contratos":
    st.title("📄 Redação de Contratos e Peças")
    tipo = st.selectbox("Tipo", ["Contrato", "Petição Inicial", "Contestação", "Procuração"])
    c1, c2 = st.columns(2)
    pa = c1.text_input("Parte A")
    pb = c2.text_input("Parte B")
    objeto = st.text_input("Objeto")
    detalhes = st.text_area("Detalhes e cláusulas desejadas")
    if st.button("Redigir"):
        if not pa or not pb or not objeto:
            st.error("Preencha Parte A, Parte B e Objeto.")
        else:
            prompt = f"Redija um {tipo} formal. Partes: {pa} e {pb}. Objeto: {objeto}. Detalhes: {detalhes}. Inclua cláusulas essenciais e cite leis aplicáveis."
            r = processar_ia(prompt, task_type="text", temperature=0.2)
            st.text_area("Minuta", r, height=400)
            checklist = processar_ia(f"Liste riscos e pontos de atenção do {tipo} acima, em tópicos.", task_type="text", temperature=0.2)
            st.markdown("### ⚠️ Checklist de riscos")
            st.write(checklist)
            if criar_docx(r): st.download_button("💾 Baixar DOCX", criar_docx(r), f"{tipo}.docx")
            add_xp(20)

# --- CARTÓRIO OCR ---
elif menu_opcao == "🏢 Cartório Digital (OCR)":
    st.title("🏢 Cartório Digital (OCR híbrido)")
    u = st.file_uploader("Imagem/PDF da Certidão", type=["jpg", "png", "pdf"])
    if u and st.button("Transcrever Inteiro Teor"):
        with st.spinner("Processando..."):
            file_bytes = u.getvalue()
            if PIL_AVAILABLE and u.type in ["image/jpeg", "image/png"]:
                img = Image.open(BytesIO(file_bytes)).convert("L")
                img = ImageOps.autocontrast(img)
                img = img.filter(ImageFilter.SHARPEN)
                buf = BytesIO()
                img.save(buf, format="PNG")
                file_bytes = buf.getvalue()
            prompt = "Transcreva fielmente como Certidão de Inteiro Teor. Indique [Selo], [Assinatura], [Livro], [Folha], [Termo], [Data]."
            r = processar_ia(prompt, file_bytes=file_bytes, task_type="vision")
            st.text_area("Resultado", r, height=400)
            if criar_docx(r): st.download_button("💾 Baixar DOCX", criar_docx(r), "InteiroTeor.docx")
            add_xp(25)

# --- TRANSCRIÇÃO ---
elif menu_opcao == "🎙️ Transcrição":
    st.title("🎙️ Transcrição de Áudio")
    tab_mic, tab_up = st.tabs(["🎤 Gravar", "📂 Upload"])
    with tab_mic:
        audio = st.audio_input("Gravar")
        if audio and st.button("Transcrever Gravação"):
            with st.spinner("Processando..."):
                r = processar_ia("", file_bytes=audio.getvalue(), task_type="audio")
                st.write(r)
                resumo = processar_ia(f"Resuma em tópicos o texto: {r}", task_type="text", temperature=0.2)
                st.markdown("### 🧾 Resumo automático")
                st.write(resumo)
                if criar_docx(r): st.download_button("Download", criar_docx(r), "Audio.docx")
                add_xp(20)
    with tab_up:
        upl = st.file_uploader("Arquivo Áudio", type=["mp3","wav","m4a"])
        if upl and st.button("Transcrever Arquivo"):
            with st.spinner("Processando..."):
                r = processar_ia("", file_bytes=upl.getvalue(), task_type="audio")
                st.write(r)
                resumo = processar_ia(f"Resuma em tópicos o texto: {r}", task_type="text", temperature=0.2)
                st.markdown("### 🧾 Resumo automático")
                st.write(resumo)
                add_xp(20)

# --- FEEDBACK ---
elif menu_opcao == "⭐ Feedback":
    st.title("⭐ Feedback")
    with st.form("feed"):
        nota = st.slider("Nota", 1, 5, 5)
        txt = st.text_area("Comentário")
        if st.form_submit_button("Enviar"):
            st.balloons()
            st.success("Enviado!")
            add_xp(50)

# --- LOGS ---
elif menu_opcao == "📊 Logs":
    st.title("📊 Logs do Sistema")
    if st.session_state.logs:
        for l in st.session_state.logs[-50:]:
            st.code(f"{l['timestamp']} | {l['task_type']} | {l['model']} | {l['latency_ms']}ms | {l['status']}")
    else:
        st.info("Sem logs.")

# --- SOBRE ---
else:
    st.title("👤 Sobre")
    st.write("Carmélio AI - v8.0 Pro")
    st.write("Desenvolvido por Arthur Carmélio.")
