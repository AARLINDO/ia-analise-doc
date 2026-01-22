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
# 0. DEPENDÊNCIAS
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
# 1. CONFIGURAÇÃO E DESIGN (PREMIUM CLEAN)
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Suíte Jurídica",
    page_icon="logo.jpg.png",
    layout="wide"
)

st.markdown("""
<style>
    /* GERAL */
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    
    /* TIMER GIGANTE (ESTILO POMOFOCUS) */
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@700&display=swap');
    
    .timer-container {
        background-color: #1F2430; /* Fundo do cartão do timer */
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        border: 1px solid #2B2F3B;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        margin-bottom: 20px;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .timer-display {
        font-family: 'Roboto Mono', monospace;
        font-size: 120px;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1;
        margin: 20px 0;
        text-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    
    .timer-label {
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 3px;
        color: #9CA3AF;
        margin-bottom: 10px;
    }

    /* BOTÕES CUSTOMIZADOS */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        transition: 0.2s;
    }
    
    /* Botão Principal (Iniciar) - Azul Vibrante */
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {
        background-color: #3B82F6;
        color: white;
        height: 55px;
        font-size: 20px;
        box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.4);
    }
    div[data-testid="stHorizontalBlock"] button[kind="primary"]:hover {
        background-color: #2563EB;
        transform: translateY(-2px);
    }

    /* PERFIL LATERAL */
    .profile-box { text-align: center; margin-bottom: 30px; margin-top: 10px; }
    .profile-name { font-weight: 700; font-size: 18px; color: #FFFFFF; margin-top: 10px; }
    .profile-role { font-size: 11px; color: #60A5FA; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 5px;}
    
    /* CARDS GERAIS */
    .question-card { background-color: #1F2430; padding: 25px; border-radius: 12px; border-left: 4px solid #3B82F6; margin-bottom: 15px; }
    
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. ESTADO GLOBAL
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

# Estado do Pomodoro
if "pomo_state" not in st.session_state: st.session_state.pomo_state = "STOPPED"
if "pomo_time_left" not in st.session_state: st.session_state.pomo_time_left = 25 * 60
if "pomo_mode" not in st.session_state: st.session_state.pomo_mode = "Foco" 
if "pomo_initial_time" not in st.session_state: st.session_state.pomo_initial_time = 25 * 60

RATE_LIMIT_SECONDS = 15

def add_xp(amount):
    st.session_state.user_xp += amount
    new_level = (st.session_state.user_xp // 100) + 1
    if new_level > st.session_state.user_level:
        st.toast(f"🎉 Subiu para Nível {new_level}!", icon="🆙")
        st.session_state.user_level = new_level
    else:
        st.toast(f"+{amount} XP", icon="⭐")

def rate_limited():
    now = time.time()
    if now - st.session_state.last_heavy_call < RATE_LIMIT_SECONDS:
        return True, RATE_LIMIT_SECONDS - (now - st.session_state.last_heavy_call)
    return False, 0

def mark_heavy_call():
    st.session_state.last_heavy_call = time.time()

def add_log(task_type, model, latency_ms, token_usage, status):
    st.session_state.logs.append({
        "task_type": task_type, "model": model, "latency_ms": latency_ms,
        "token_usage": token_usage, "status": status, "timestamp": datetime.now().isoformat()
    })

if not st.session_state.lgpd_ack:
    with st.expander("🔐 Acesso ao Sistema", expanded=True):
        st.write("Ao entrar, você concorda com o processamento de dados via IA para fins de estudo.")
        if st.button("Entrar no Sistema"):
            st.session_state.lgpd_ack = True
            st.rerun()
    st.stop()

# =============================================================================
# 3. BACKEND (GROQ)
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
    except Exception: return None

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
        add_log(task_type, model_override or "auto", int((time.time()-start)*1000), 0, f"error: {e}")
        return f"❌ Erro na IA: {str(e)}"

def validate_json_response(response_text):
    try:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match: return json.loads(match.group(0))
    except: pass
    return None

def validate_question_json(data):
    try:
        assert set(data.keys()) == {"enunciado", "alternativas", "gabarito", "comentario"}
        assert all(k in data["alternativas"] for k in ["A", "B", "C", "D", "E"])
        return True, ""
    except AssertionError: return False, "Formato inválido."

def extract_json_from_text(text):
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None

# =============================================================================
# 5. SIDEBAR
# =============================================================================
with st.sidebar:
    try: st.image("logo.jpg.png", use_container_width=True)
    except: st.warning("Logo não encontrada.")
    
    # --- PERFIL FINAL ---
    st.markdown("""
    <div class="profile-box">
        <small style="color: #9CA3AF;">Desenvolvido por</small><br>
        <div class="profile-name">Arthur Carmélio</div>
        <div class="profile-role">ESPECIALISTA NOTARIAL</div>
    </div>
    """, unsafe_allow_html=True)

    c_lvl, c_xp = st.columns(2)
    c_lvl.metric("Nível", st.session_state.user_level)
    c_xp.metric("XP", st.session_state.user_xp)
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))

    st.markdown("---")
    menu_opcao = st.radio("Navegação:",
        ["🎓 Área do Estudante", "💬 Mentor Jurídico", "📄 Redação de Contratos", "🏢 Cartório Digital (OCR)", "🎙️ Transcrição", "⭐ Feedback", "📊 Logs", "👤 Sobre"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    col_link, col_zap = st.columns(2)
    with col_link: st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")
    with col_zap: st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720?text=Suporte%20Carmelio%20AI)")

# =============================================================================
# 6. CONSTANTES
# =============================================================================
DISCIPLINAS = [
    "Direito Constitucional", "Direito Administrativo", "Direito Penal", "Direito Civil",
    "Processo Penal", "Processo Civil", "Direito Tributário", "Direito do Trabalho",
    "Notarial e Registral", "Ética Profissional", "Português", "RLM", "Informática"
]
BANCAS = ["FGV", "Cebraspe", "Vunesp", "FCC", "AOCP", "Comperve", "IBFC", "Quadrix"]
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO", "Federal"]

# =============================================================================
# 7. MÓDULOS
# =============================================================================

# --- MÓDULO 1: ESTUDANTE ---
if menu_opcao == "🎓 Área do Estudante":
    st.title("🎓 Área do Estudante Pro")
    tab_questoes, tab_edital, tab_pomodoro, tab_flash, tab_crono = st.tabs(["📝 Banco Infinito", "🎯 Mestre dos Editais", "🍅 Sala de Foco", "⚡ Flashcards", "📅 Cronograma"])

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
                else: st.error("Erro na geração. Tente novamente.")

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
        file = st.file_uploader("Upload Edital (PDF/DOCX)", type=["pdf", "docx"])
        if st.button("Verticalizar"):
            if file:
                with st.spinner("IA Analisando..."):
                    r = processar_ia(f"Verticalize este edital: {file.name}", temperature=0.1)
                    st.markdown(r)
                    add_xp(20)

    # 1.3 SALA DE FOCO (VISUAL LIMPO E CENTRALIZADO)
    with tab_pomodoro:
        st.markdown("### 🍅 Sala de Foco")
        
        # --- SELETORES DE MODO (NO TOPO) ---
        c_mode1, c_mode2, c_mode3 = st.columns(3)
        if c_mode1.button("🧠 Foco (25m)", use_container_width=True):
            st.session_state.pomo_mode = "Foco"
            st.session_state.pomo_time_left = 25 * 60
            st.session_state.pomo_initial_time = 25 * 60
            st.session_state.pomo_state = "STOPPED"
            st.rerun()
        if c_mode2.button("☕ Curto (5m)", use_container_width=True):
            st.session_state.pomo_mode = "Descanso Curto"
            st.session_state.pomo_time_left = 5 * 60
            st.session_state.pomo_initial_time = 5 * 60
            st.session_state.pomo_state = "STOPPED"
            st.rerun()
        if c_mode3.button("🧘 Longo (15m)", use_container_width=True):
            st.session_state.pomo_mode = "Descanso Longo"
            st.session_state.pomo_time_left = 15 * 60
            st.session_state.pomo_initial_time = 15 * 60
            st.session_state.pomo_state = "STOPPED"
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # --- CONTAINER PRINCIPAL DO TIMER ---
        # Calculo do tempo
        mins, secs = divmod(st.session_state.pomo_time_left, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        
        # HTML do Timer
        st.markdown(f"""
        <div class="timer-container">
            <div class="timer-label">{st.session_state.pomo_mode}</div>
            <div class="timer-display">{time_str}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Barra de Progresso
        progresso = 1.0
        if st.session_state.pomo_initial_time > 0:
            progresso = st.session_state.pomo_time_left / st.session_state.pomo_initial_time
        st.progress(progresso)

        # --- BOTÕES DE AÇÃO ---
        c_play, c_pause, c_reset = st.columns(3)
        
        if c_play.button("COMEÇAR", type="primary", use_container_width=True):
            st.session_state.pomo_state = "RUNNING"
            st.rerun()
            
        if c_pause.button("PAUSAR", use_container_width=True):
            st.session_state.pomo_state = "PAUSED"
            st.rerun()
            
        if c_reset.button("ZERAR", use_container_width=True):
            st.session_state.pomo_state = "STOPPED"
            st.session_state.pomo_time_left = st.session_state.pomo_initial_time
            st.rerun()

        # Lógica do Loop
        if st.session_state.pomo_state == "RUNNING":
            if st.session_state.pomo_time_left > 0:
                time.sleep(1)
                st.session_state.pomo_time_left -= 1
                st.rerun()
            else:
                st.session_state.pomo_state = "STOPPED"
                st.balloons()
                add_xp(50)
                st.markdown("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", unsafe_allow_html=True)

        st.markdown("---")
        # Rádio Lofi (Discreta)
        with st.expander("🎵 Música de Fundo (Lofi Radio)", expanded=False):
            st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")

    # 1.4 FLASHCARDS
    with tab_flash:
        st.markdown("### ⚡ Flashcards")
        tema = st.text_input("Tema para memorizar")
        if st.button("Criar Flashcard"):
            r = processar_ia(f"Crie flashcard sobre {tema}. Retorne: PERGUNTA --- RESPOSTA")
            if "---" in r:
                f, b = r.split("---")
                st.session_state.cards.append({"front": f.strip(), "back": b.strip()})
                st.success("Criado!")
                add_xp(5)
            else: st.error("Erro formato.")
            
        if st.session_state.cards:
            st.write(f"Total: {len(st.session_state.cards)}")
            for i, c in enumerate(st.session_state.cards):
                st.info(f"Card {i+1}: {c['front']}")
            csv = "front,back\n" + "\n".join([f"{c['front']},{c['back']}" for c in st.session_state.cards])
            st.download_button("💾 Baixar Anki CSV", csv, "anki.csv")

    # 1.5 CRONOGRAMA
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
    st.write("Carmélio AI - v10.1 Stable")
    st.write("Desenvolvido por Arthur Carmélio.")
