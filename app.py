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

# =============================================================================
# 0. DEPENDÊNCIAS OPCIONAIS (PARA NÃO QUEBRAR NO DEPLOY)
# =============================================================================
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import docx as docx_reader
    DOCX_READER_AVAILABLE = True
except ImportError:
    DOCX_READER_AVAILABLE = False

try:
    from PIL import Image, ImageFilter, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

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
    /* GERAL */
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    
    /* CARDS & CONTAINERS */
    .question-card { background-color: #1F2430; padding: 20px; border-radius: 12px; border-left: 5px solid #3B82F6; margin-bottom: 15px; }
    .flashcard { background: linear-gradient(135deg, #1F2430 0%, #282C34 100%); padding: 24px; border-radius: 12px; border: 1px solid #3B82F6; text-align: center; }
    .xp-badge { background-color: #FFD700; color: #000; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 12px; }
    
    /* POMODORO TIMER ESPECÍFICO */
    .timer-display {
        font-size: 90px; font-weight: bold; color: #FFFFFF; text-align: center;
        text-shadow: 0 0 30px rgba(59, 130, 246, 0.6); margin: 20px 0; font-family: 'Courier New', monospace;
    }
    .timer-status {
        font-size: 22px; text-transform: uppercase; letter-spacing: 3px; color: #3B82F6; text-align: center; margin-bottom: 10px;
    }
    
    /* INPUTS & BUTTONS */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #161922; border: 1px solid #2B2F3B; color: #E0E7FF; border-radius: 8px;
    }
    .stButton>button {
        width: 100%; border-radius: 8px; height: 45px; font-weight: 600; border: none;
        background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%);
        color: white; transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4); color: white;}
    
    /* PERFIL */
    .profile-box { text-align: center; margin-bottom: 20px; color: #E0E7FF; }
    .profile-name { font-weight: bold; font-size: 18px; margin-top: 5px; color: #FFFFFF; }
    .profile-role { font-size: 12px; color: #3B82F6; text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. ESTADO, GAMIFICAÇÃO & LOGS
# =============================================================================
if "user_xp" not in st.session_state: st.session_state.user_xp = 0
if "user_level" not in st.session_state: st.session_state.user_level = 1
if "edital_text" not in st.session_state: st.session_state.edital_text = ""
if "edital_topics" not in st.session_state: st.session_state.edital_topics = []
if "generated_questions" not in st.session_state: st.session_state.generated_questions = []
if "focus_sessions" not in st.session_state: st.session_state.focus_sessions = []
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

# LGPD CHECK
if not st.session_state.lgpd_ack:
    with st.expander("🔐 LGPD e Tratamento de Dados (Clique para ler)", expanded=True):
        st.markdown("""
        **Termos de Uso do Carmélio AI:**
        - Este sistema utiliza Inteligência Artificial para processar textos e imagens.
        - Seus dados são processados pela Groq API e não são retidos permanentemente.
        - Ao continuar, você concorda com o processamento para fins de estudo e produtividade.
        """)
        if st.button("Concordo e quero entrar"):
            st.session_state.lgpd_ack = True
            st.rerun()
    st.stop()

# =============================================================================
# 3. BACKEND (GROQ API)
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
        # Roteamento
        if task_type == "vision":
            model = "llama-3.2-11b-vision-preview"
        elif task_type == "audio":
            model = "whisper-large-v3"
        else:
            model = model_override if model_override else "llama-3.3-70b-versatile"

        # Vision
        if task_type == "vision" and file_bytes:
            b64 = base64.b64encode(file_bytes).decode('utf-8')
            content = client.chat.completions.create(
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt},{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
                model=model, temperature=0.1
            ).choices[0].message.content
            add_log("vision", model, int((time.time()-start)*1000), len(prompt), "ok")
            return content

        # Audio
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

        # Text
        else:
            content = client.chat.completions.create(
                messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}],
                model=model, temperature=temperature
            ).choices[0].message.content
            add_log("text", model, int((time.time()-start)*1000), len(prompt), "ok")
            return content

    except Exception as e:
        add_log(task_type, model_override or "auto", int((time.time()-start)*1000), 0, f"error: {e}")
        return f"❌ Erro na IA: {str(e)}"

# =============================================================================
# 4. VALIDAÇÃO & UTILITÁRIOS
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
        return True, ""
    except AssertionError:
        return False, "Formato inválido."

def extract_json_from_text(text):
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None

# =============================================================================
# 5. SIDEBAR (COMPLETA)
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
        ["🎓 Área do Estudante", "💬 Mentor Jurídico", "📄 Redação de Contratos", "🏢 Cartório Digital (OCR)", "🎙️ Transcrição", "🍅 Sala de Foco (Pomodoro)", "⭐ Feedback", "📊 Logs", "👤 Sobre"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    col_link, col_zap = st.columns(2)
    with col_link:
        st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")
    with col_zap:
        st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720?text=Suporte%20Carmelio%20AI)")

# =============================================================================
# 6. CONSTANTES GLOBAIS
# =============================================================================
DISCIPLINAS = [
    "Direito Constitucional", "Direito Administrativo", "Direito Penal", "Direito Civil",
    "Processo Penal", "Processo Civil", "Direito Tributário", "Direito do Trabalho",
    "Notarial e Registral", "Ética Profissional", "Português", "RLM", "Informática",
    "Direito Financeiro", "Criminologia", "Direitos Humanos"
]
BANCAS = ["FGV", "Cebraspe", "Vunesp", "FCC", "AOCP", "Comperve", "IBFC", "Quadrix"]
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO", "Federal"]

# =============================================================================
# 7. MÓDULOS
# =============================================================================

# --- MÓDULO 1: ESTUDANTE ---
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
                prompt = (
                    "Gere 1 questão inédita em JSON com campos: enunciado, alternativas (A,B,C,D,E), gabarito (A–E), comentario. "
                    f"Disciplina: {disc}. Assunto: {assunto}. Banca: {banca}. Cargo: {cargo}. Jurisdição: {uf}. "
                    f"Nível: {nivel}. Cite artigos/súmulas. Retorne APENAS JSON."
                )
                res = processar_ia(prompt, task_type="text", temperature=0.3)
                data = validate_json_response(res)
                if data and validate_question_json(data)[0]:
                    st.session_state.q_atual = data
                    st.session_state.ver_resp = False
                    add_xp(10)
                else:
                    st.error("Erro na geração. Tente novamente.")

        if 'q_atual' in st.session_state:
            q = st.session_state.q_atual
            st.markdown(f"<div class='question-card'><h4>{disc} | {banca} | {uf}</h4><p>{q['enunciado']}</p></div>", unsafe_allow_html=True)
            for k in ["A","B","C","D","E"]: st.write(f"**{k})** {q['alternativas'].get(k, '')}")
            
            if st.button("👁️ Ver Gabarito"): st.session_state.ver_resp = True
            if st.session_state.get('ver_resp'):
                st.success(f"Gabarito: {q['gabarito']}")
                st.info(f"Comentário: {q['comentario']}")
                st.session_state.generated_questions.append(q)
                if criar_docx(json.dumps(q, indent=2), "Questão"):
                    st.download_button("💾 Baixar DOCX", criar_docx(json.dumps(q, indent=2), "Questão"), "Questao.docx")

    # 1.2 MESTRE DOS EDITAIS
    with tab_edital:
        st.markdown("### 🎯 Verticalizador de Editais")
        col_up, col_txt = st.columns(2)
        with col_up:
            file = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf", "docx", "txt"])
        with col_txt:
            texto_manual = st.text_area("Ou cole o texto aqui:", height=150)

        def extract_text(f):
            if f.type == "application/pdf":
                if PDFPLUMBER_AVAILABLE:
                    import pdfplumber
                    with pdfplumber.open(BytesIO(f.getvalue())) as pdf:
                        return "".join([p.extract_text() or "" for p in pdf.pages])
                return "Erro: pdfplumber não instalado."
            elif "word" in f.type:
                if DOCX_READER_AVAILABLE:
                    import docx
                    doc = docx.Document(BytesIO(f.getvalue()))
                    return "\n".join([p.text for p in doc.paragraphs])
                return "Erro: python-docx não instalado."
            else:
                return f.getvalue().decode("utf-8", errors="ignore")

        if st.button("📊 Verticalizar Edital"):
            text = ""
            if file: text = extract_text(file)
            elif texto_manual: text = texto_manual
            
            if len(text) > 50:
                st.session_state.edital_text = text
                with st.spinner("Analisando..."):
                    prompt = f"Analise este edital e extraia os tópicos por matéria. Retorne uma lista organizada. Texto: {text[:4000]}..."
                    r = processar_ia(prompt, temperature=0.1)
                    st.markdown(r)
                    if criar_docx(r): st.download_button("💾 Baixar DOCX", criar_docx(r), "Edital_Vertical.docx")
                    add_xp(20)
            else:
                st.warning("Texto inválido ou curto.")

    # 1.3 FLASHCARDS
    with tab_flash:
        st.markdown("### ⚡ Flashcards")
        tema = st.text_input("Tema para memorizar")
        if st.button("Criar Flashcard"):
            r = processar_ia(f"Crie um flashcard sobre {tema}. Retorne: PERGUNTA --- RESPOSTA")
            if "---" in r:
                f, b = r.split("---")
                st.session_state.cards.append({"front": f.strip(), "back": b.strip()})
                st.success("Criado!")
                add_xp(5)
            else: st.error("Erro formato.")
            
        if st.session_state.cards:
            st.write(f"Total: {len(st.session_state.cards)}")
            for i, c in enumerate(st.session_state.cards):
                st.text(f"Card {i+1}: {c['front']}")
            csv = "front,back\n" + "\n".join([f"{c['front']},{c['back']}" for c in st.session_state.cards])
            st.download_button("💾 Baixar Anki CSV", csv, "anki.csv")

    # 1.4 CRONOGRAMA
    with tab_crono:
        st.markdown("### 📅 Cronograma")
        h = st.slider("Horas/dia", 1, 8, 4)
        topicos = st.text_area("Listar tópicos (um por linha)")
        if st.button("Gerar Plano"):
            topics = [t for t in topicos.split('\n') if t.strip()]
            plan = []
            base = datetime.today()
            for i, t in enumerate(topics):
                d = base + timedelta(days=i)
                plan.append(f"{d.strftime('%d/%m')} - {t} ({h}h)")
            res = "\n".join(plan)
            st.text_area("Resultado", res, height=300)
            if criar_docx(res): st.download_button("💾 Baixar Plano", criar_docx(res), "Plano.docx")
            add_xp(15)

# --- MÓDULO POMODORO (SALA DE FOCO) ---
elif menu_opcao == "🍅 Sala de Foco (Pomodoro)":
    st.title("🍅 Sala de Foco & Produtividade")

    # Opções exatas das suas imagens
    modo_foco = st.radio("Selecione o ciclo:", [
        "Passos de bebê (10 min)", "Popular (20 min)", "Médio (40 min)", "Estendido (60 min)", "Personalizado"
    ], index=2, horizontal=True)

    if modo_foco == "Personalizado":
        tempo_selecionado = st.slider("Minutos:", 5, 120, 25)
    else:
        # Extrai número do texto (ex: "Médio (40 min)" -> 40)
        tempo_selecionado = int(re.search(r'\d+', modo_foco).group())

    col1, col2 = st.columns(2)
    with col1:
        som = st.selectbox("Alarme:", ["Ding", "Bip", "Mudo"])
    with col2:
        notificacao = st.toggle("Notificar ao terminar", value=True)

    st.markdown("---")

    col_timer = st.columns([1, 2, 1])[1]
    with col_timer:
        if st.button("▶️ INICIAR SESSÃO", use_container_width=True):
            status_text = st.empty()
            timer_text = st.empty()
            progresso = st.progress(0)

            total_segundos = tempo_selecionado * 60
            inicio = datetime.now()

            for i in range(total_segundos):
                restante = total_segundos - i
                mins, secs = divmod(restante, 60)
                time_str = f"{mins:02d}:{secs:02d}"

                timer_text.markdown(f"<div class='timer-display'>{time_str}</div>", unsafe_allow_html=True)
                status_text.markdown(f"<div class='timer-status'>FOCADO • {modo_foco}</div>", unsafe_allow_html=True)
                progresso.progress((i + 1) / total_segundos)
                time.sleep(1)

            # Fim
            timer_text.markdown(f"<div class='timer-display'>00:00</div>", unsafe_allow_html=True)
            st.balloons()
            st.success(f"🎉 Ciclo de {tempo_selecionado} min concluído!")
            
            # Registrar
            fim = datetime.now()
            st.session_state.focus_sessions.append({
                "modo": modo_foco, "inicio": inicio.strftime("%H:%M"), 
                "fim": fim.strftime("%H:%M"), "duracao": tempo_selecionado
            })
            add_xp(tempo_selecionado * 2)

            if som != "Mudo":
                st.markdown("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", unsafe_allow_html=True)
            
            if notificacao:
                st.toast("⏰ Seu ciclo de foco terminou!", icon="⌛")

    st.markdown("---")
    st.markdown("### 📊 Histórico de sessões")
    if st.session_state.focus_sessions:
        for s in st.session_state.focus_sessions[-10:]:
            st.write(f"- **{s['modo']}**: {s['inicio']} às {s['fim']} ({s['duracao']} min)")
    else:
        st.info("Nenhuma sessão registrada ainda.")

# --- MENTOR ---
elif menu_opcao == "💬 Mentor Jurídico":
    st.title("💬 Mentor Jurídico")
    perfil = st.selectbox("Perfil", ["Professor Didático", "Doutrinador (Técnico)", "Jurisprudencial"])
    if "chat" not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat: st.chat_message(m["role"]).write(m["content"])
    
    if p := st.chat_input("Dúvida..."):
        st.session_state.chat.append({"role":"user", "content":p})
        st.chat_message("user").write(p)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                sys = f"Atue como {perfil}. Cite leis."
                r = processar_ia(p, system_instruction=sys)
                st.write(r)
                st.session_state.chat.append({"role":"assistant", "content":r})
                add_xp(5)
    
    st.markdown("---")
    st.markdown("### ✅ Checklist de Riscos")
    caso = st.text_area("Descreva o caso")
    if st.button("Gerar Checklist"):
        r = processar_ia(f"Gere checklist de riscos para: {caso}", temperature=0.2)
        st.write(r)

# --- CONTRATOS ---
elif menu_opcao == "📄 Redação de Contratos":
    st.title("📄 Redação de Contratos")
    tipo = st.selectbox("Tipo", ["Contrato", "Petição", "Procuração"])
    c1, c2 = st.columns(2)
    pa = c1.text_input("Parte A")
    pb = c2.text_input("Parte B")
    detalhes = st.text_area("Detalhes")
    if st.button("Redigir"):
        if pa and pb and detalhes:
            with st.spinner("Escrevendo..."):
                prompt = f"Redija {tipo}. Parte A: {pa}. Parte B: {pb}. Detalhes: {detalhes}. Formal."
                r = processar_ia(prompt, temperature=0.2)
                st.text_area("Minuta", r, height=400)
                if criar_docx(r): st.download_button("💾 Baixar", criar_docx(r), f"{tipo}.docx")
                add_xp(20)
        else: st.error("Preencha os campos.")

# --- CARTÓRIO OCR ---
elif menu_opcao == "🏢 Cartório Digital (OCR)":
    st.title("🏢 Cartório Digital")
    st.info("Usa Visão Computacional para transcrever certidões.")
    u = st.file_uploader("Imagem da Certidão", type=["jpg", "png", "pdf"])
    if u and st.button("Transcrever Inteiro Teor"):
        with st.spinner("Lendo..."):
            file_bytes = u.getvalue()
            # Otimização com PIL se possível
            if PIL_AVAILABLE and u.type in ["image/jpeg", "image/png"]:
                try:
                    img = Image.open(BytesIO(file_bytes)).convert("L")
                    img = ImageOps.autocontrast(img)
                    buf = BytesIO(); img.save(buf, format="PNG")
                    file_bytes = buf.getvalue()
                except: pass
            
            r = processar_ia("Transcreva fielmente como Inteiro Teor. Indique [Selo], [Assinatura].", file_bytes=file_bytes, task_type="vision")
            st.text_area("Resultado", r, height=400)
            if criar_docx(r): st.download_button("💾 Baixar", criar_docx(r), "InteiroTeor.docx")
            add_xp(25)

# --- TRANSCRIÇÃO ---
elif menu_opcao == "🎙️ Transcrição":
    st.title("🎙️ Transcrição")
    tab_mic, tab_up = st.tabs(["🎤 Gravar", "📂 Upload"])
    with tab_mic:
        audio = st.audio_input("Gravar")
        if audio and st.button("Transcrever Gravação"):
            with st.spinner("Processando..."):
                r = processar_ia("", file_bytes=audio.getvalue(), task_type="audio")
                st.write(r)
                if criar_docx(r): st.download_button("Download", criar_docx(r), "Audio.docx")
                summ = processar_ia(f"Resuma: {r}")
                st.info("Resumo:"); st.write(summ)
                add_xp(20)
    with tab_up:
        upl = st.file_uploader("Arquivo", type=["mp3","wav","m4a"])
        if upl and st.button("Transcrever Arquivo"):
            with st.spinner("Processando..."):
                r = processar_ia("", file_bytes=upl.getvalue(), task_type="audio")
                st.write(r)
                summ = processar_ia(f"Resuma: {r}")
                st.info("Resumo:"); st.write(summ)
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
    st.title("📊 Logs")
    if st.session_state.logs:
        for l in st.session_state.logs[-20:]:
            st.code(f"{l['timestamp']} | {l['task_type']} | {l['status']}")
    else: st.info("Sem logs.")

# --- SOBRE ---
else:
    st.title("👤 Sobre")
    st.write("Carmélio AI - v9.0 Master")
    st.write("Desenvolvido por Arthur Carmélio.")
