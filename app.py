# app.py
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

# Opcional: bibliotecas para leitura de PDF/DOCX (verticalização de edital)
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

# =============================================================================
# 1. CONFIGURAÇÃO E DESIGN
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Suíte Jurídica Pro",
    page_icon="logo.jpg.png",
    layout="wide"
)

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
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. SISTEMA DE GAMIFICAÇÃO & ESTADO
# =============================================================================
if "user_xp" not in st.session_state: st.session_state.user_xp = 0
if "user_level" not in st.session_state: st.session_state.user_level = 1
if "edital_text" not in st.session_state: st.session_state.edital_text = ""
if "edital_topics" not in st.session_state: st.session_state.edital_topics = []
if "generated_questions" not in st.session_state: st.session_state.generated_questions = []
if "logs" not in st.session_state: st.session_state.logs = []
if "lgpd_ack" not in st.session_state: st.session_state.lgpd_ack = False
if "last_heavy_call" not in st.session_state: st.session_state.last_heavy_call = 0.0

RATE_LIMIT_SECONDS = 20

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

# =============================================================================
# 3. BACKEND ROBUSTO (API GROQ REAL)
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
        return True, ""
    except AssertionError:
        return False, "Formato inválido. Campos obrigatórios ausentes ou incorretos."

def extract_json_from_text(text):
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

# =============================================================================
# 4. LGPD
# =============================================================================
with st.expander("LGPD e Tratamento de Dados"):
    st.markdown("""
    **Aviso:** Este sistema processa textos, imagens e áudios para gerar conteúdo jurídico e educacional.
    - Finalidade: estudo, minuta e transcrição.
    - Base legal: execução de contrato/legítimo interesse.
    - Retenção: opcional; você pode optar por não armazenar conteúdo.
    - Direitos: acesso, correção, exclusão.
    """)
    st.session_state.lgpd_ack = st.checkbox("Li e concordo com o tratamento de dados", value=st.session_state.lgpd_ack)
if not st.session_state.lgpd_ack:
    st.stop()
opt_out = st.sidebar.checkbox("Não armazenar conteúdo (opt-out)", value=True)

# =============================================================================
# 5. BARRA LATERAL (LOGO, LINKS E NAVEGAÇÃO)
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
        <div class="profile-role">Especialista Notarial & Dev</div>
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

    with st.expander("🍅 Pomodoro Timer"):
        tempo = st.slider("Minutos", 15, 60, 25)
        if st.button("Iniciar Foco"):
            st.toast(f"Foco de {tempo} minutos iniciado!")

    st.markdown("---")
    col_link, col_zap = st.columns(2)
    with col_link:
        st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")
    with col_zap:
        st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720?text=Suporte%20Carmelio%20AI)")

# =============================================================================
# 6. LISTAS EXPANDIDAS
# =============================================================================
DISCIPLINAS = [
    "Direito Constitucional", "Direito Administrativo", "Direito Penal", "Direito Civil",
    "Processo Penal", "Processo Civil", "Direito Tributário", "Direito do Trabalho",
    "Processo do Trabalho", "Direito Empresarial", "Direitos Humanos", "Direito Ambiental",
    "Direito Internacional", "Notarial e Registral", "Português", "RLM", "Informática", "Ética Profissional"
]
BANCAS = ["FGV", "Cebraspe", "Vunesp", "FCC", "AOCP", "Comperve", "IBFC", "Quadrix"]
UFS = ["SC", "SP", "RJ", "MG", "RS", "PR", "BA", "PE", "CE", "DF", "GO", "ES", "MT", "MS", "PA", "AM", "RN", "PB", "PI", "RO", "RR", "TO", "AC", "AL", "AP", "SE"]

# =============================================================================
# 7. MÓDULOS DO SISTEMA
# =============================================================================

# --- MÓDULO 1: ESTUDANTE PRO ---
if menu_opcao == "🎓 Área do Estudante":
    st.title("🎓 Área do Estudante Pro")
    tab_questoes, tab_edital, tab_flash, tab_crono = st.tabs(["📝 Banco Infinito", "🎯 Mestre dos Editais", "⚡ Flashcards", "📅 Cronograma"])

    # 1.1 BANCO DE QUESTÕES (JSON VALIDADO + Nível + UF)
    with tab_questoes:
        st.markdown("### 🔎 Gerador de Questões Inéditas")
        c1, c2, c3, c4 = st.columns(4)
        disc = c1.selectbox("Disciplina", DISCIPLINAS)
        banca = c2.selectbox("Estilo Banca", BANCAS)
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
                    "Cite artigos e precedentes quando aplicável. Retorne APENAS JSON."
                )
                res = processar_ia(prompt, task_type="text", temperature=0.2)
                data = validate_json_response(res)
                if data:
                    ok, msg = validate_question_json(data)
                    if not ok:
                        st.error(msg)
                        st.code(json.dumps(data, ensure_ascii=False, indent=2))
                    else:
                        st.session_state.q_atual = data
                        st.session_state.ver_resp = False
                        add_xp(10)
                else:
                    st.error("Erro na geração. Tente novamente.")

        if 'q_atual' in st.session_state:
            q = st.session_state.q_atual
            st.markdown(f"<div class='question-card'><h4>{disc} | {banca} | {uf} | {nivel}</h4><p>{q['enunciado']}</p></div>", unsafe_allow_html=True)
            st.write("Alternativas:")
            for k, v in q['alternativas'].items():
                st.write(f"**{k})** {v}")
            if st.button("👁️ Ver Gabarito"):
                st.session_state.ver_resp = True
            if st.session_state.get('ver_resp'):
                st.success(f"Gabarito: {q['gabarito']}")
                st.info(f"Comentário: {q['comentario']}")
                if criar_docx(json.dumps(q, ensure_ascii=False, indent=2), "Questão (JSON)"):
                    st.download_button("💾 Baixar JSON em DOCX", criar_docx(json.dumps(q, ensure_ascii=False, indent=2), "Questão (JSON)"), "Questao_JSON.docx")

    # 1.2 MESTRE DOS EDITAIS (UPLOAD + VERTICALIZAÇÃO + TREINAMENTO POR TÓPICO)
    with tab_edital:
        st.markdown("### 🎯 Verticalizador de Editais")
        col_up, col_txt = st.columns(2)
        with col_up:
            file = st.file_uploader("Upload do edital (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
        with col_txt:
            texto_edital = st.text_area("Cole o Edital aqui:", height=150)

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
                return None, "python-docx (reader) não instalado."
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

        c_v, c_s = st.columns(2)
        if c_v.button("📊 Verticalizar Edital"):
            limited, wait = rate_limited()
            if limited:
                st.warning(f"Aguarde {int(wait)}s para nova operação pesada.")
            else:
                mark_heavy_call()
                text = ""
                err = None
                if file:
                    if file.type == "application/pdf":
                        text, err = extract_text_from_pdf(file.getvalue())
                    elif file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"]:
                        text, err = extract_text_from_docx(file.getvalue())
                    elif file.type == "text/plain":
                        try:
                            text = file.getvalue().decode("utf-8", errors="ignore")
                        except Exception as e:
                            err = f"Erro ao ler TXT: {e}"
                    else:
                        err = "Formato não suportado."
                else:
                    text = texto_edital

                if err:
                    st.error(err)
                elif not text or len(text.strip()) < 50:
                    st.warning("Texto do edital muito curto. Verifique o upload ou cole o conteúdo completo.")
                else:
                    st.session_state.edital_text = text
                    topics = verticalize_edital(text)
                    st.session_state.edital_topics = topics
                    st.success(f"Tópicos extraídos: {len(topics)} matérias.")
                    for item in topics[:10]:
                        st.markdown(f"- **{item['materia']}**: {min(len(item['topicos']), 5)} tópicos")
                    if criar_docx(json.dumps(topics, ensure_ascii=False, indent=2), "Edital Verticalizado"):
                        st.download_button("💾 Baixar tópicos (DOCX)", criar_docx(json.dumps(topics, ensure_ascii=False, indent=2), "Edital Verticalizado"), "Edital_Verticalizado.docx")
                    add_xp(20)

        if c_s.button("📝 Criar Simulado do Edital"):
            if st.session_state.edital_text:
                with st.spinner("Criando simulado..."):
                    p = f"Crie 3 questões baseadas nos tópicos deste edital: {st.session_state.edital_text}"
                    r = processar_ia(p)
                    st.write(r)
                    add_xp(30)
            else:
                st.warning("Primeiro verticalize o edital.")

        st.markdown("---")
        st.markdown("### 🎯 Treinar IA por tópico")
        if not st.session_state.edital_topics:
            st.info("Nenhum edital processado ainda. Faça upload ou cole o texto e clique em Verticalizar.")
        else:
            materias = [t["materia"] for t in st.session_state.edital_topics]
            materia_sel = st.selectbox("Matéria", sorted(set(materias)))
            topicos = []
            for t in st.session_state.edital_topics:
                if t["materia"] == materia_sel:
                    topicos.extend(t["topicos"])
            topico_sel = st.selectbox("Tópico", topicos)
            banca_t = st.selectbox("Banca simulada", BANCAS)
            cargo_t = st.text_input("Cargo", "Analista Judiciário")
            uf_t = st.selectbox("UF/Tribunal", UFS)
            nivel_t = st.selectbox("Nível de dificuldade", ["Fácil", "Médio", "Difícil"])

            if st.button("🧠 Gerar questão inédita do tópico"):
                limited, wait = rate_limited()
                if limited:
                    st.warning(f"Aguarde {int(wait)}s para nova operação pesada.")
                else:
                    mark_heavy_call()
                    nivel_instr = {
                        "Fácil": "Use linguagem simples, conceito básico e alternativa correta evidente.",
                        "Médio": "Exija interpretação e aplicação prática moderada, com alternativas plausíveis.",
                        "Difícil": "Inclua nuances, jurisprudência e pegadinhas típicas da banca."
                    }[nivel_t]
                    prompt = (
                        "Gere 1 questão inédita em JSON com campos: enunciado, alternativas (A,B,C,D,E), gabarito (A–E), comentario. "
                        f"Matéria: {materia_sel}. Tópico: {topico_sel}. Banca: {banca_t}. Cargo: {cargo_t}. Jurisdição: {uf_t}. "
                        f"Nível: {nivel_t}. {nivel_instr} "
                        "Cite artigos e precedentes quando aplicável. Retorne APENAS JSON."
                    )
                    r = processar_ia(prompt, task_type="text", system_instruction="Você é examinador de banca. Seja técnico e cite lei.", temperature=0.2)
                    data = extract_json_from_text(r)
                    if not data:
                        st.error("Falha ao obter JSON válido. Tente novamente.")
                    else:
                        ok, msg = validate_question_json(data)
                        if not ok:
                            st.error(msg)
                            st.code(json.dumps(data, ensure_ascii=False, indent=2))
                        else:
                            st.session_state.generated_questions.append(data)
                            st.success("Questão gerada e validada.")
                            st.markdown(f"<div class='question-card'><b>Enunciado:</b> {data['enunciado']}</div>", unsafe_allow_html=True)
                            st.write("Alternativas:")
                            for k in ["A", "B", "C", "D", "E"]:
                                st.write(f"{k}) {data['alternativas'][k]}")
                            st.info(f"Gabarito: {data['gabarito']}")
                            st.write("Comentário:")
                            st.write(data["comentario"])
                            if criar_docx(json.dumps(data, ensure_ascii=False, indent=2), "Questão (JSON)"):
                                st.download_button("💾 Baixar JSON em DOCX", criar_docx(json.dumps(data, ensure_ascii=False, indent=2), "Questão (JSON)"), "Questao_JSON.docx")
                            add_xp(25)

        st.markdown("---")
        st.markdown("### 📦 Histórico de questões geradas")
        if st.session_state.generated_questions:
            st.write(f"Total: {len(st.session_state.generated_questions)}")
            for i, q in enumerate(st.session_state.generated_questions[-10:], 1):
                st.write(f"**{i}.** {q['enunciado'][:120]}...")
            if criar_docx(json.dumps(st.session_state.generated_questions, ensure_ascii=False, indent=2), "Histórico de Questões"):
                st.download_button("💾 Baixar histórico (DOCX)", criar_docx(json.dumps(st.session_state.generated_questions, ensure_ascii=False, indent=2), "Histórico de Questões"), "Questoes_Historico.docx")
        else:
            st.info("Nenhuma questão gerada ainda.")

    # 1.3 FLASHCARDS COM ANKI
    with tab_flash:
        st.markdown("### ⚡ Flashcards & Exportação Anki")
        tema = st.text_input("Tema do Flashcard")
        if "cards" not in st.session_state: st.session_state.cards = []

        if st.button("Criar Flashcard"):
            r = processar_ia(f"Crie um flashcard sobre {tema}. Retorne: PERGUNTA --- RESPOSTA")
            if "---" in r:
                f, b = r.split("---", 1)
                st.session_state.cards.append((f.strip(), b.strip()))
                st.success("Criado!")
                add_xp(5)
            else:
                st.error("Erro formato.")

        if st.session_state.cards:
            st.write(f"Você tem {len(st.session_state.cards)} cartas.")
            csv = "front,back\n" + "\n".join([f"{f.strip().replace(',', ';')},{b.strip().replace(',', ';')}" for f,b in st.session_state.cards])
            st.download_button("💾 Baixar CSV para Anki", csv, "anki_deck.csv")
            st.markdown("#### Sugestão de revisão (SM-2 simplificado)")
            for i, (f, b) in enumerate(st.session_state.cards, 1):
                st.write(f"- Carta {i}: revisar em 1, 3, 7 e 14 dias.")

    # 1.4 CRONOGRAMA
    with tab_crono:
        st.markdown("### 📅 Cronograma Inteligente")
        h = st.slider("Horas/Dia", 1, 8, 4)
        obj = st.text_input("Objetivo", "Concurso Cartório")
        topicos = st.text_area("Tópicos (um por linha)", "Constitucional - Direitos Fundamentais\nPenal - Crimes contra a pessoa\nProc. Penal - Inquérito")
        if st.button("Gerar Plano"):
            topics = [t.strip() for t in topicos.split("\n") if t.strip()]
            base_date = datetime.today()
            intervals = [1, 3, 7, 14]
            plan = []
            for i, t in enumerate(topics):
                study_day = base_date + timedelta(days=i)
                plan.append(f"{study_day.date().isoformat()} — {t} — {h}h")
                for k, d in enumerate(intervals):
                    rev_day = study_day + timedelta(days=d)
                    plan.append(f"{rev_day.date().isoformat()} — Revisão {k+1}: {t} — {max(1, h//2)}h")
            formatted = "\n".join(plan)
            st.text_area("Plano", formatted, height=300)
            if criar_docx(formatted, "Cronograma de Estudos"):
                st.download_button("💾 Baixar DOCX", criar_docx(formatted, "Cronograma de Estudos"), "Cronograma.docx")
            add_xp(15)

# --- MÓDULO 2: MENTOR JURÍDICO ---
elif menu_opcao == "💬 Mentor Jurídico":
    st.title("💬 Mentor Jurídico")
    perfil = st.selectbox("Perfil", ["Professor Didático", "Doutrinador (Técnico)", "Jurisprudencial"])
    exigir_fontes = st.checkbox("Exigir fontes (artigos, súmulas, precedentes)", value=True)

    if "chat" not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat:
        st.chat_message(m["role"]).write(m["content"])

    sys_msg = {
        "Professor Didático": "Use exemplos e analogias. Estruture em tópicos simples.",
        "Doutrinador (Técnico)": "Seja técnico e cite lei e doutrina.",
        "Jurisprudencial": "Foque em precedentes STF/STJ, temas e súmulas."
    }[perfil]

    if p := st.chat_input("Dúvida jurídica..."):
        st.session_state.chat.append({"role": "user", "content": p})
        st.chat_message("user").write(p)
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                prompt = p
                if exigir_fontes:
                    prompt += "\n\nExija citação de artigos, súmulas e precedentes com identificação."
                r = processar_ia(prompt, task_type="text", system_instruction=sys_msg, temperature=0.2)
                st.write(r)
                st.session_state.chat.append({"role": "assistant", "content": r})
                add_xp(10)

    st.markdown("---")
    st.markdown("### Checklist jurídico automático")
    caso = st.text_area("Detalhes do caso/objeto", height=120)
    tipo_doc = st.selectbox("Tipo", ["Contrato", "Petição Inicial", "Contestação", "Habeas Corpus", "Procuração"])
    if st.button("Gerar checklist"):
        prompt = (
            f"Com base no caso: {caso}, gere um checklist de riscos e pontos obrigatórios para {tipo_doc}. "
            "Estruture em tópicos: partes, objeto, preço/prazo, foro, LGPD, garantias, penalidades, jurisprudência relevante."
        )
        r = processar_ia(prompt, task_type="text", system_instruction="Seja técnico e objetivo.", temperature=0.2)
        st.write(r)
        if criar_docx(r, "Checklist Jurídico"):
            st.download_button("💾 Baixar DOCX", criar_docx(r, "Checklist Jurídico"), "Checklist.docx")
        add_xp(15)

# --- MÓDULO 3: CONTRATOS ---
elif menu_opcao == "📄 Redação de Contratos":
    st.title("📄 Redação de Contratos")
    tipo = st.selectbox("Documento", ["Contrato", "Petição", "Procuração"])
    c1, c2 = st.columns(2)
    pa = c1.text_input("Parte A")
    pb = c2.text_input("Parte B")
    detalhes = st.text_area("Detalhes")

    st.markdown("### Cláusulas modulares")
    clausulas = {
        "Foro": st.checkbox("Foro"),
        "Confidencialidade": st.checkbox("Confidencialidade"),
        "LGPD": st.checkbox("LGPD"),
        "Multa": st.checkbox("Multa"),
        "Reajuste": st.checkbox("Reajuste"),
        "Garantias": st.checkbox("Garantias")
    }

    if st.button("Redigir"):
        if detalhes:
            prompt = (
                f"Redija um {tipo}. Parte A: {pa}. Parte B: {pb}. Detalhes: {detalhes}. Linguagem formal. "
                "Inclua as cláusulas selecionadas: " + ", ".join([k for k, v in clausulas.items() if v]) + "."
            )
            r = processar_ia(prompt, model_override="llama-3.3-70b-versatile", temperature=0.2)
            st.text_area("Minuta", r, height=400)
            if criar_docx(r, f"{tipo} Profissional"):
                st.download_button("💾 Baixar DOCX", criar_docx(r, f"{tipo} Profissional"), f"{tipo}.docx")
            add_xp(20)
        else:
            st.error("Preencha os detalhes do caso.")

# --- MÓDULO 4: CARTÓRIO OCR (VISION REAL) ---
elif menu_opcao == "🏢 Cartório Digital (OCR)":
    st.title("🏢 Cartório Digital (Vision AI)")
    st.info("Usa Visão Computacional para transcrever certidões antigas.")
    u = st.file_uploader("Imagem da Certidão", type=["jpg", "png"])
    if u and st.button("📝 Transcrever Inteiro Teor"):
        limited, wait = rate_limited()
        if limited:
            st.warning(f"Aguarde {int(wait)}s para nova operação pesada.")
        else:
            mark_heavy_call()
            with st.spinner("Lendo documento manuscrito..."):
                prompt = "Transcreva este documento fielmente. Formate como Certidão de Inteiro Teor. Indique [Selo] e [Assinatura]."
                r = processar_ia(prompt, file_bytes=u.getvalue(), task_type="vision")
                st.text_area("Transcrição", r, height=400)
                if criar_docx(r, "Certidão de Inteiro Teor"):
                    st.download_button("💾 Baixar DOCX", criar_docx(r, "Certidão de Inteiro Teor"), "Inteiro_Teor.docx")
                add_xp(25)

# --- MÓDULO 5: TRANSCRIÇÃO (MIC + UPLOAD) ---
elif menu_opcao == "🎙️ Transcrição":
    st.title("🎙️ Transcrição de Áudio")
    tab_mic, tab_up = st.tabs(["🎤 Gravar", "📂 Upload"])

    with tab_mic:
        audio = st.audio_input("Gravar")
        if audio and st.button("Transcrever Gravação"):
            limited, wait = rate_limited()
            if limited:
                st.warning(f"Aguarde {int(wait)}s para nova operação pesada.")
            else:
                mark_heavy_call()
                with st.spinner("Ouvindo..."):
                    r = processar_ia("", file_bytes=audio.getvalue(), task_type="audio")
                    # Diarização simples (placeholder)
                    r = "[Falante 1 00:00–00:30] " + str(r) + "\n[Falante 2 00:30–01:00] ..."
                    st.write(r)
                    if criar_docx(r, "Transcrição de Áudio"):
                        st.download_button("Download", criar_docx(r, "Transcrição de Áudio"), "Audio.docx")
                    add_xp(20)

    with tab_up:
        upl = st.file_uploader("Arquivo MP3/WAV/M4A", type=["mp3", "wav", "m4a"])
        if upl and st.button("Transcrever Arquivo"):
            limited, wait = rate_limited()
            if limited:
                st.warning(f"Aguarde {int(wait)}s para nova operação pesada.")
            else:
                mark_heavy_call()
                with st.spinner("Processando..."):
                    r = processar_ia("", file_bytes=upl.getvalue(), task_type="audio")
                    r = "[Falante 1 00:00–00:30] " + str(r) + "\n[Falante 2 00:30–01:00] ..."
                    st.write(r)
                    add_xp(20)

# --- MÓDULO 6: FEEDBACK ---
elif menu_opcao == "⭐ Feedback":
    st.title("⭐ Avalie o Carmélio AI")
    with st.form("feed"):
        nota = st.slider("Nota", 1, 5, 5)
        msg = st.text_area("Sugestão")
        if st.form_submit_button("Enviar"):
            st.balloons()
            st.success("Obrigado pelo feedback!")
            add_xp(50)

# --- MÓDULO 7: LOGS ---
elif menu_opcao == "📊 Logs":
    st.title("📊 Logs e Observabilidade")
    if st.session_state.logs:
        st.write(f"Total de eventos: {len(st.session_state.logs)}")
        for log in st.session_state.logs[-50:]:
            st.write(f"[{log['timestamp']}] {log['task_type']} | {log['model']} | {log['latency_ms']}ms | tokens={log['token_usage']} | {log['status']}")
    else:
        st.info("Sem logs ainda.")

# --- SOBRE ---
else:
    st.title("👤 Sobre o Autor")
    c1, c2 = st.columns([1,2])
    with c1:
        try: st.image("logo.jpg.png", width=200)
        except: st.write("⚖️")
    with c2:
        st.markdown("""
        ### Arthur Carmélio
        **Desenvolvedor & Especialista Jurídico**

        O **Carmélio AI** nasceu da necessidade de unir a tradição do Direito com a velocidade da Tecnologia.

        * 🎓 Bacharel em Direito
        * 📜 Especialista Notarial
        * 💻 Desenvolvedor Python

        ---
        **Contato:**
        * [LinkedIn](https://www.linkedin.com/in/arthurcarmelio/)
        * [WhatsApp](https://wa.me/5548920039720)
        """)
