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
# 1. DEPENDÊNCIAS E CONFIGURAÇÃO
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Suíte Jurídica",
    page_icon="logo.jpg.png",
    layout="wide"
)

# Tentativa de importação segura
try: import pdfplumber
except ImportError: pdfplumber = None
try: import docx as docx_reader
except ImportError: docx_reader = None
try: from PIL import Image, ImageFilter, ImageOps
except ImportError: Image = None

# =============================================================================
# 2. ESTILOS CSS (DESIGN PREMIUM)
# =============================================================================
st.markdown("""
<style>
    /* GERAL */
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    
    /* POMODORO TIMER */
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@700&display=swap');
    .timer-container {
        background-color: #1F2430; border-radius: 20px; padding: 40px;
        text-align: center; border: 1px solid #2B2F3B; margin: 0 auto 30px auto;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 600px;
    }
    .timer-display {
        font-family: 'Roboto Mono', monospace; font-size: 130px; font-weight: 700;
        color: #FFFFFF; line-height: 1; margin: 10px 0;
        text-shadow: 0 0 25px rgba(59, 130, 246, 0.5);
    }
    .timer-label {
        font-family: 'Inter', sans-serif; font-size: 18px; text-transform: uppercase;
        letter-spacing: 4px; color: #60A5FA; margin-bottom: 10px; font-weight: 600;
    }

    /* BOTÕES */
    .stButton>button {
        border-radius: 10px; font-weight: 600; height: 50px; border: none; transition: 0.2s;
    }
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white; font-size: 18px; box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.4);
    }
    div[data-testid="stHorizontalBlock"] button[kind="primary"]:hover {
        transform: scale(1.02);
    }

    /* PERFIL */
    .profile-box { text-align: center; margin-bottom: 30px; margin-top: 10px; }
    .profile-dev { font-size: 12px; color: #9CA3AF; margin-bottom: 2px; }
    .profile-name { font-weight: 700; font-size: 20px; color: #FFFFFF; }
    
    /* CARDS */
    .question-card { background-color: #1F2430; padding: 25px; border-radius: 12px; border-left: 4px solid #3B82F6; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 3. GESTÃO DE ESTADO E UTILITÁRIOS
# =============================================================================
# Inicialização segura de variáveis
DEFAULTS = {
    "user_xp": 0, "user_level": 1,
    "edital_text": "", "edital_topics": [],
    "generated_questions": [], "logs": [], "cards": [],
    "lgpd_ack": False, "last_heavy_call": 0.0,
    # Pomodoro
    "pomo_state": "STOPPED", "pomo_mode": "Foco", 
    "pomo_duration": 25 * 60, "pomo_end_time": None,
    "pomo_auto_start": False
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

RATE_LIMIT_SECONDS = 5 # Tempo entre chamadas pesadas

def check_rate_limit():
    """Impede spam de cliques na API"""
    now = time.time()
    if now - st.session_state.last_heavy_call < RATE_LIMIT_SECONDS:
        st.warning(f"⏳ Aguarde alguns segundos...")
        return True
    return False

def mark_call():
    st.session_state.last_heavy_call = time.time()

def add_xp(amount):
    st.session_state.user_xp += amount
    new_level = (st.session_state.user_xp // 100) + 1
    if new_level > st.session_state.user_level:
        st.toast(f"🎉 Subiu para Nível {new_level}!", icon="🆙")
        st.session_state.user_level = new_level
    else:
        st.toast(f"+{amount} XP", icon="⭐")

def extract_json_safe(text):
    """Extrai JSON de forma robusta procurando tags <json> ou chaves {}"""
    match = re.search(r"<json>(.*?)</json>", text, re.DOTALL)
    json_str = match.group(1) if match else None
    
    if not json_str:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        json_str = match.group(0) if match else None
        
    if json_str:
        try: return json.loads(json_str)
        except: return None
    return None

def create_docx(text, title="Documento Carmélio AI"):
    try:
        doc = Document()
        doc.add_heading(title, 0)
        for p in str(text).split('\n'):
            if p.strip(): doc.add_paragraph(p)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except: return None

# =============================================================================
# 4. MOTOR DE IA (GROQ)
# =============================================================================
def get_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return None
    return Groq(api_key=api_key)

def call_ai(prompt, file_bytes=None, type="text", system="Você é um assistente útil.", temp=0.3):
    if check_rate_limit(): return None
    client = get_client()
    if not client: return "⚠️ Configure a GROQ_API_KEY."
    
    mark_call()
    try:
        if type == "text":
            r = client.chat.completions.create(
                messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
                model="llama-3.3-70b-versatile", temperature=temp
            )
            return r.choices[0].message.content
            
        elif type == "vision" and file_bytes:
            b64 = base64.b64encode(file_bytes).decode('utf-8')
            r = client.chat.completions.create(
                messages=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}],
                model="llama-3.2-11b-vision-preview", temperature=0.1
            )
            return r.choices[0].message.content
            
        elif type == "audio" and file_bytes:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tmp.write(file_bytes); tmp_path = tmp.name
            with open(tmp_path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), f.read()),
                    model="whisper-large-v3", response_format="text", language="pt"
                )
            os.unlink(tmp_path)
            return transcription
            
    except Exception as e:
        return f"Erro na IA: {e}"

# =============================================================================
# 5. SIDEBAR
# =============================================================================
with st.sidebar:
    try: st.image("logo.jpg.png", use_container_width=True)
    except: pass
    
    st.markdown("""
    <div class="profile-box">
        <div class="profile-dev">Desenvolvido por</div>
        <div class="profile-name">Arthur Carmélio</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("Nível", st.session_state.user_level)
    c2.metric("XP", st.session_state.user_xp)
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))
    
    st.markdown("---")
    menu = st.radio("Navegação:", 
        ["🎯 Mestre dos Editais", "🍅 Sala de Foco", "⚡ Flashcards", "📅 Cronograma", "💬 Mentor Jurídico", "📄 Redação", "🏢 Cartório OCR", "🎙️ Transcrição", "⭐ Feedback"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720)")

# LGPD Bloqueio
if not st.session_state.lgpd_ack:
    with st.expander("🔐 Acesso ao Sistema", expanded=True):
        st.write("Ao entrar, você concorda com o uso de IA para processamento de dados.")
        if st.button("Entrar no Sistema"):
            st.session_state.lgpd_ack = True
            st.rerun()
    st.stop()

# =============================================================================
# 6. MÓDULOS DO SISTEMA
# =============================================================================

# --- MESTRE DOS EDITAIS (Consolidado) ---
if menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais & Questões")
    st.caption("Central de Inteligência: Verticalize editais e gere provas personalizadas.")

    with st.container():
        c_up, c_inf = st.columns([1, 2])
        with c_up:
            file = st.file_uploader("📂 Upload Edital (PDF/DOCX)", type=["pdf", "docx"])
        with c_inf:
            if not st.session_state.edital_text:
                st.info("👈 **Comece aqui:** Suba seu edital. A IA organizará os tópicos e habilitará o modo de treino focado.")
            else:
                st.success("✅ Edital ativo!")
                if st.button("🗑️ Limpar"):
                    st.session_state.edital_text = ""
                    st.rerun()

    # Processamento Automático do Edital
    if file and not st.session_state.edital_text:
        with st.spinner("🧠 Lendo edital..."):
            raw = "Conteúdo extraído..."
            if file.type == "application/pdf" and pdfplumber:
                with pdfplumber.open(BytesIO(file.getvalue())) as pdf: raw = "".join([p.extract_text() or "" for p in pdf.pages])
            elif "word" in file.type and docx_reader:
                doc = docx_reader.Document(BytesIO(file.getvalue()))
                raw = "\n".join([p.text for p in doc.paragraphs])
            
            st.session_state.edital_text = raw
            st.rerun()

    st.markdown("---")
    
    # Gerador de Questões
    st.subheader("📝 Gerador de Questões")
    modo = st.radio("Modo:", ["🎲 Aleatório", "🎯 Focado no Edital"], horizontal=True, disabled=not st.session_state.edital_text)
    
    c1, c2, c3, c4 = st.columns(4)
    if modo == "🎯 Focado no Edital" and st.session_state.edital_text:
        disc = "Geral do Edital"
        assunto = "Tópicos do edital carregado"
        st.info(f"Gerando questões com base no arquivo carregado.")
    else:
        disc = c1.selectbox("Disciplina", ["Constitucional", "Administrativo", "Penal", "Civil", "Proc. Penal", "Notarial"])
        assunto = c2.text_input("Assunto", "Atos Administrativos")
    
    banca = c3.selectbox("Banca", ["FGV", "Cebraspe", "Vunesp", "FCC"])
    nivel = c4.selectbox("Nível", ["Médio", "Difícil", "Juiz"])

    if st.button("🚀 Gerar Questão", type="primary", use_container_width=True):
        with st.spinner("Elaborando..."):
            ctx = st.session_state.edital_text[:4000] if modo == "🎯 Focado no Edital" else ""
            prompt = (
                f"Crie uma questão inédita. Banca: {banca}. Nível: {nivel}. Disciplina: {disc}. Assunto: {assunto}. "
                f"Contexto (se houver): {ctx}. "
                "Retorne JSON dentro de <json>...</json> com chaves: enunciado, alternativas (dict A-E), gabarito, comentario."
            )
            res = call_ai(prompt, temp=0.4)
            data = extract_json_safe(res)
            
            if data:
                st.session_state.q_atual = data
                st.session_state.ver_resp = False
                add_xp(10)
            else:
                st.error("Erro na geração. Tente novamente.")

    if 'q_atual' in st.session_state:
        q = st.session_state.q_atual
        st.markdown(f"<div class='question-card'><h5>{banca} | {nivel}</h5><p style='font-size:18px; color:white;'>{q.get('enunciado')}</p></div>", unsafe_allow_html=True)
        for k, v in q.get('alternativas', {}).items():
            st.write(f"**{k})** {v}")
        
        if st.button("👁️ Ver Resposta"): st.session_state.ver_resp = True
        if st.session_state.get('ver_resp'):
            st.success(f"Gabarito: {q.get('gabarito')}")
            st.info(f"📝 {q.get('comentario')}")

# --- SALA DE FOCO (POMODORO INTELIGENTE) ---
elif menu == "🍅 Sala de Foco":
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 1. Seletor de Modo
    c_m1, c_m2, c_m3 = st.columns(3)
    def set_pomo(mode, min):
        st.session_state.pomo_mode = mode
        st.session_state.pomo_duration = min * 60
        st.session_state.pomo_state = "STOPPED"
        st.session_state.pomo_end_time = None
        st.rerun()

    if c_m1.button("🧠 FOCO (25m)", use_container_width=True): set_pomo("Foco", 25)
    if c_m2.button("☕ CURTO (5m)", use_container_width=True): set_pomo("Descanso", 5)
    if c_m3.button("🧘 LONGO (15m)", use_container_width=True): set_pomo("Longo", 15)

    # 2. Lógica do Timer (Timestamp - Não trava)
    remaining = st.session_state.pomo_duration
    if st.session_state.pomo_state == "RUNNING":
        now = time.time()
        if now >= st.session_state.pomo_end_time:
            # Acabou
            st.session_state.pomo_state = "STOPPED"
            st.balloons()
            st.markdown("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", unsafe_allow_html=True)
            add_xp(50)
            
            # Auto-Start Lógica
            if st.session_state.pomo_auto_start:
                next_mode = "Descanso" if st.session_state.pomo_mode == "Foco" else "Foco"
                next_min = 5 if next_mode == "Descanso" else 25
                st.session_state.pomo_mode = next_mode
                st.session_state.pomo_duration = next_min * 60
                st.session_state.pomo_end_time = time.time() + (next_min * 60)
                st.session_state.pomo_state = "RUNNING"
                st.toast(f"Iniciando {next_mode}...", icon="🔄")
                time.sleep(2)
                st.rerun()
            else:
                remaining = 0
        else:
            remaining = int(st.session_state.pomo_end_time - now)
            time.sleep(1)
            st.rerun()

    # 3. Visualização
    mins, secs = divmod(remaining, 60)
    time_str = f"{mins:02d}:{secs:02d}"
    
    st.markdown(f"""
    <div class="timer-container">
        <div class="timer-label">{st.session_state.pomo_mode}</div>
        <div class="timer-display">{time_str}</div>
    </div>
    """, unsafe_allow_html=True)

    # 4. Controles
    c_play, c_pause, c_reset = st.columns(3)
    
    if c_play.button("COMEÇAR", type="primary", use_container_width=True):
        if st.session_state.pomo_state != "RUNNING":
            st.session_state.pomo_state = "RUNNING"
            st.session_state.pomo_end_time = time.time() + remaining
            st.rerun()
            
    if c_pause.button("PAUSAR", use_container_width=True):
        if st.session_state.pomo_state == "RUNNING":
            st.session_state.pomo_state = "PAUSED"
            st.session_state.pomo_duration = remaining # Salva onde parou
            st.rerun()
            
    if c_reset.button("ZERAR", use_container_width=True):
        st.session_state.pomo_state = "STOPPED"
        defaults = {"Foco": 25, "Descanso": 5, "Longo": 15}
        st.session_state.pomo_duration = defaults.get(st.session_state.pomo_mode, 25) * 60
        st.rerun()

    st.session_state.pomo_auto_start = st.checkbox("🔄 Iniciar ciclos automaticamente?", value=st.session_state.pomo_auto_start)

    with st.expander("🎵 Rádio Lofi", expanded=False):
        st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")

# --- FLASHCARDS ---
elif menu == "⚡ Flashcards":
    st.title("⚡ Flashcards AI")
    tema = st.text_input("Assunto")
    if st.button("Criar"):
        res = call_ai(f"Crie flashcard sobre {tema}. Retorne JSON <json>{{'front':'...', 'back':'...'}}</json>")
        data = extract_json_safe(res)
        if data:
            st.session_state.cards.append(data)
            st.success("Criado!")
            add_xp(5)
    
    if st.session_state.cards:
        for i, c in enumerate(st.session_state.cards):
            with st.expander(f"Card {i+1}: {c.get('front')}"):
                st.write(c.get('back'))

# --- CRONOGRAMA ---
elif menu == "📅 Cronograma":
    st.title("📅 Cronograma Inteligente")
    h = st.slider("Horas diárias", 1, 10, 4)
    obj = st.text_input("Objetivo (Ex: OAB)")
    if st.button("Gerar"):
        res = call_ai(f"Crie cronograma semanal para {obj} com {h}h/dia.")
        st.write(res)
        add_xp(20)

# --- MENTOR ---
elif menu == "💬 Mentor Jurídico":
    st.title("💬 Mentor Jurídico")
    if p:=st.chat_input("Dúvida?"):
        res = call_ai(p, system="Seja um professor de direito didático.")
        st.write(res)

# --- REDAÇÃO ---
elif menu == "📄 Redação":
    st.title("📄 Redação Jurídica")
    tipo = st.selectbox("Documento", ["Contrato", "Petição"])
    det = st.text_area("Detalhes")
    if st.button("Escrever"):
        st.write(call_ai(f"Escreva {tipo}: {det}"))

# --- OCR ---
elif menu == "🏢 Cartório OCR":
    st.title("🏢 Cartório Digital")
    u = st.file_uploader("Imagem")
    if u and st.button("Ler"):
        st.write(call_ai("Transcreva.", file_bytes=u.getvalue(), type="vision"))

# --- TRANSCRIÇÃO ---
elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição")
    a = st.audio_input("Gravar")
    if a and st.button("Transcrever"):
        st.write(call_ai("", file_bytes=a.getvalue(), type="audio"))

# --- FEEDBACK ---
elif menu == "⭐ Feedback":
    st.title("⭐ Feedback")
    st.write("Envie sua sugestão!")

# --- SOBRE ---
else:
    st.title("👤 Sobre")
    st.write("Carmélio AI - v14.0 Master")
    st.write("Desenvolvido por Arthur Carmélio.")
