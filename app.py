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
# 0. DEPENDÊNCIAS OPCIONAIS
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
    
    /* CARDS */
    .question-card { background-color: #1F2430; padding: 20px; border-radius: 12px; border-left: 5px solid #3B82F6; margin-bottom: 15px; }
    .flashcard { background: linear-gradient(135deg, #1F2430 0%, #282C34 100%); padding: 24px; border-radius: 12px; border: 1px solid #3B82F6; text-align: center; }
    .xp-badge { background-color: #FFD700; color: #000; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 12px; }
    
    /* POMODORO ESPECÍFICO */
    .timer-display {
        font-size: 100px; font-weight: 800; color: #FFFFFF; text-align: center;
        text-shadow: 0 0 40px rgba(59, 130, 246, 0.4); margin: 10px 0; font-family: 'Courier New', monospace;
    }
    .timer-label {
        font-size: 18px; color: #9CA3AF; text-align: center; text-transform: uppercase; letter-spacing: 2px;
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

# --- ESTADO DO POMODORO ---
if "pomo_state" not in st.session_state: st.session_state.pomo_state = "STOPPED" # STOPPED, RUNNING
if "pomo_time_left" not in st.session_state: st.session_state.pomo_time_left = 25 * 60
if "pomo_mode" not in st.session_state: st.session_state.pomo_mode = "Foco" # Foco, Curto, Longo
if "pomo_initial_time" not in st.session_state: st.session_state.pomo_initial_time = 25 * 60

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
        "task_type": task_type, "model": model, "latency_ms": latency_ms,
        "token_usage": token_usage, "status": status, "timestamp": datetime.now().isoformat()
    })

# LGPD
if not st.session_state.lgpd_ack:
    with st.expander("🔐 LGPD e Termos de Uso", expanded=True):
        st.markdown("Seus dados são processados pela Groq API e não são retidos. Concorda?")
        if st.button("Concordo"):
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

    with st.expander("🍅 Pomodoro Rápido"):
        if st.button("Foco 25min"): st.toast("Foco iniciado!")

    st.markdown("---")
    col_link, col_zap = st.columns(2)
    with col_link: st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")
    with col_zap: st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720?text=Suporte%20Carmelio%20AI)")

# =============================================================================
# 7. MÓDULOS
# =============================================================================

# --- ESTUDANTE PRO ---
if menu_opcao == "🎓 Área do Estudante":
    st.title("🎓 Área do Estudante Pro")
    tab_questoes, tab_edital, tab_pomodoro, tab_flash, tab_crono = st.tabs(["📝 Banco Infinito", "🎯 Mestre dos Editais", "🍅 Sala de Foco", "⚡ Flashcards", "📅 Cronograma"])

    # 1.1 QUESTÕES
    with tab_questoes:
        st.markdown("### 🔎 Gerador de Questões")
        c1, c2, c3, c4 = st.columns(4)
        disc = c1.selectbox("Disciplina", ["Direito Constitucional", "Administrativo", "Penal", "Civil", "Proc. Penal", "Notarial", "Português", "Informática"])
        banca = c2.selectbox("Banca", ["FGV", "Cebraspe", "Vunesp", "FCC"])
        uf = c3.selectbox("UF", ["SC", "SP", "RJ", "DF", "Federal"])
        nivel = c4.selectbox("Nível", ["Fácil", "Médio", "Difícil"])
        assunto = st.text_input("Assunto", placeholder="Ex: Atos Administrativos")
        cargo = st.text_input("Cargo", placeholder="Ex: Escrevente")

        if st.button("Gerar Questão"):
            with st.spinner("Criando..."):
                prompt = (f"Gere 1 questão inédita em JSON. Disciplina: {disc}. Assunto: {assunto}. Banca: {banca}. Cargo: {cargo}. Jurisdição: {uf}. Nível: {nivel}. Retorne APENAS JSON.")
                res = processar_ia(prompt, task_type="text", temperature=0.3)
                data = validate_json_response(res)
                if data and validate_question_json(data)[0]:
                    st.session_state.q_atual = data
                    st.session_state.ver_resp = False
                    add_xp(10)
                else: st.error("Erro na geração.")

        if 'q_atual' in st.session_state:
            q = st.session_state.q_atual
            st.markdown(f"<div class='question-card'><h4>{disc} | {banca}</h4><p>{q['enunciado']}</p></div>", unsafe_allow_html=True)
            for k in ["A","B","C","D","E"]: st.write(f"**{k})** {q['alternativas'].get(k, '')}")
            if st.button("👁️ Ver Gabarito"): st.session_state.ver_resp = True
            if st.session_state.get('ver_resp'):
                st.success(f"Gabarito: {q['gabarito']}")
                st.info(f"Comentário: {q['comentario']}")

    # 1.2 MESTRE DOS EDITAIS
    with tab_edital:
        st.markdown("### 🎯 Verticalizador")
        file = st.file_uploader("Upload Edital (PDF/DOCX)", type=["pdf", "docx"])
        if st.button("Verticalizar"):
            if file:
                st.info("Processando...")
                # Lógica simplificada de extração
                text = "Texto extraído simulado"
                if file.type == "application/pdf" and PDFPLUMBER_AVAILABLE:
                    import pdfplumber
                    with pdfplumber.open(BytesIO(file.getvalue())) as pdf: text = "".join([p.extract_text() for p in pdf.pages])
                
                with st.spinner("IA Analisando..."):
                    r = processar_ia(f"Verticalize este edital: {text[:3000]}", temperature=0.1)
                    st.markdown(r)
                    add_xp(20)

    # 1.3 SALA DE FOCO (POMODORO CORRIGIDO)
    with tab_pomodoro:
        st.markdown("### 🍅 Sala de Foco & Produtividade")
        
        # --- Controles Superiores ---
        c_modos, c_extra = st.columns([2, 1])
        with c_modos:
            mode_cols = st.columns(3)
            if mode_cols[0].button("🧠 Foco (25m)", use_container_width=True):
                st.session_state.pomo_mode = "Foco"
                st.session_state.pomo_time_left = 25 * 60
                st.session_state.pomo_initial_time = 25 * 60
                st.session_state.pomo_state = "STOPPED"
                st.rerun()
            
            if mode_cols[1].button("☕ Curto (5m)", use_container_width=True):
                st.session_state.pomo_mode = "Curto"
                st.session_state.pomo_time_left = 5 * 60
                st.session_state.pomo_initial_time = 5 * 60
                st.session_state.pomo_state = "STOPPED"
                st.rerun()

            if mode_cols[2].button("🧘 Longo (15m)", use_container_width=True):
                st.session_state.pomo_mode = "Longo"
                st.session_state.pomo_time_left = 15 * 60
                st.session_state.pomo_initial_time = 15 * 60
                st.session_state.pomo_state = "STOPPED"
                st.rerun()

        # --- Seletor de Tempo Personalizado (só aparece em Foco) ---
        if st.session_state.pomo_mode == "Foco":
            st.write("Configurar tempo de Foco:")
            preset = st.radio("Presets:", ["Passos de bebê (10m)", "Popular (25m)", "Médio (40m)", "Estendido (60m)"], index=1, horizontal=True, label_visibility="collapsed")
            # Atualiza tempo se estiver parado
            if st.session_state.pomo_state == "STOPPED":
                new_time = int(re.search(r'\d+', preset).group()) * 60
                if new_time != st.session_state.pomo_initial_time:
                    st.session_state.pomo_time_left = new_time
                    st.session_state.pomo_initial_time = new_time

        # --- Visual do Timer ---
        mins, secs = divmod(st.session_state.pomo_time_left, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        
        st.markdown(f"""
        <div class="timer-display">{time_str}</div>
        <div class="timer-label">{st.session_state.pomo_mode}</div>
        """, unsafe_allow_html=True)
        
        # Barra de Progresso
        progresso = 1.0 - (st.session_state.pomo_time_left / st.session_state.pomo_initial_time)
        st.progress(progresso)

        # --- Botões de Ação (Play/Pause/Reset) ---
        c_play, c_pause, c_reset = st.columns(3)
        
        if c_play.button("▶️ INICIAR", use_container_width=True, type="primary"):
            st.session_state.pomo_state = "RUNNING"
            st.rerun()
            
        if c_pause.button("⏸️ PAUSAR", use_container_width=True):
            st.session_state.pomo_state = "PAUSED"
            st.rerun()
            
        if c_reset.button("🔄 ZERAR", use_container_width=True):
            st.session_state.pomo_state = "STOPPED"
            st.session_state.pomo_time_left = st.session_state.pomo_initial_time
            st.rerun()

        # --- Lógica do Loop (Só roda se RUNNING) ---
        if st.session_state.pomo_state == "RUNNING":
            if st.session_state.pomo_time_left > 0:
                time.sleep(1) # Aguarda 1s
                st.session_state.pomo_time_left -= 1
                st.rerun() # Recarrega a página para atualizar o timer
            else:
                st.session_state.pomo_state = "STOPPED"
                st.balloons()
                st.success("Ciclo Concluído!")
                add_xp(50)
                # Toca som
                st.markdown("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", unsafe_allow_html=True)

        # --- Rádio Lofi ---
        with st.expander("🎵 Rádio Lofi (Música de Fundo)", expanded=False):
            st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")

    # 1.4 FLASHCARDS
    with tab_flash:
        st.markdown("### ⚡ Flashcards")
        tema = st.text_input("Tema")
        if st.button("Criar Flashcard"):
            r = processar_ia(f"Crie flashcard sobre {tema}. Retorne: PERGUNTA --- RESPOSTA")
            if "---" in r:
                f, b = r.split("---")
                st.session_state.cards.append({"front": f, "back": b})
                st.success("Criado!")
                add_xp(5)
        
        if st.session_state.cards:
            for i, c in enumerate(st.session_state.cards):
                st.info(f"Card {i+1}: {c['front']}")

    # 1.5 CRONOGRAMA
    with tab_crono:
        st.markdown("### 📅 Cronograma")
        h = st.slider("Horas/dia", 1, 8, 4)
        topicos = st.text_area("Tópicos")
        if st.button("Gerar"):
            r = processar_ia(f"Crie cronograma para {topicos} com {h}h/dia.")
            st.write(r)
            add_xp(15)

# --- MENTOR ---
elif menu_opcao == "💬 Mentor Jurídico":
    st.title("💬 Mentor Jurídico")
    if "chat" not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat: st.chat_message(m["role"]).write(m["content"])
    
    if p := st.chat_input("Dúvida..."):
        st.session_state.chat.append({"role":"user", "content":p})
        st.chat_message("user").write(p)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                r = processar_ia(p)
                st.write(r)
                st.session_state.chat.append({"role":"assistant", "content":r})
                add_xp(5)

# --- CONTRATOS ---
elif menu_opcao == "📄 Redação de Contratos":
    st.title("📄 Redação de Contratos")
    tipo = st.selectbox("Tipo", ["Contrato", "Petição"])
    detalhes = st.text_area("Detalhes")
    if st.button("Redigir"):
        with st.spinner("Escrevendo..."):
            r = processar_ia(f"Redija {tipo}: {detalhes}", temperature=0.2)
            st.write(r)
            add_xp(20)

# --- CARTÓRIO OCR ---
elif menu_opcao == "🏢 Cartório Digital (OCR)":
    st.title("🏢 Cartório Digital")
    u = st.file_uploader("Imagem", type=["jpg", "png", "pdf"])
    if u and st.button("Transcrever"):
        with st.spinner("Lendo..."):
            r = processar_ia("Transcreva como Inteiro Teor.", file_bytes=u.getvalue(), task_type="vision")
            st.write(r)
            add_xp(25)

# --- TRANSCRIÇÃO ---
elif menu_opcao == "🎙️ Transcrição":
    st.title("🎙️ Transcrição")
    tab_mic, tab_up = st.tabs(["🎤 Gravar", "📂 Upload"])
    with tab_mic:
        audio = st.audio_input("Gravar")
        if audio and st.button("Transcrever"):
            with st.spinner("Processando..."):
                r = processar_ia("", file_bytes=audio.getvalue(), task_type="audio")
                st.write(r)
                add_xp(20)
    with tab_up:
        upl = st.file_uploader("Arquivo", type=["mp3","wav"])
        if upl and st.button("Transcrever"):
            with st.spinner("Processando..."):
                r = processar_ia("", file_bytes=upl.getvalue(), task_type="audio")
                st.write(r)
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
    st.write("Carmélio AI - v9.2 Definitiva")
    st.write("Desenvolvido por Arthur Carmélio.")
