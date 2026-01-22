import streamlit as st
from groq import Groq
from docx import Document
from io import BytesIO
from datetime import datetime
import json
import base64
import time
import re

# =============================================================================
# 1. CONFIGURAÇÃO E DESIGN (GEMINI STYLE)
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Suíte Jurídica",
    page_icon="✨",
    layout="wide"
)

# Tentativa de importação segura
try: import pdfplumber
except ImportError: pdfplumber = None
try: import docx as docx_reader
except ImportError: docx_reader = None
try: from PIL import Image, ImageFilter, ImageOps
except ImportError: Image = None

st.markdown("""
<style>
    /* GERAL */
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    
    /* GEMINI GRADIENT TEXT */
    .gemini-text {
        background: -webkit-linear-gradient(45deg, #4285F4, #9B72CB, #D96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.5rem;
    }
    
    /* CARDS */
    .stChatInput { border-radius: 20px; }
    .question-card { 
        background: linear-gradient(135deg, #1F2937 0%, #111827 100%); 
        padding: 20px; border-radius: 15px; 
        border: 1px solid #374151; margin-bottom: 10px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* POMODORO TIMER */
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@700&display=swap');
    .timer-display {
        font-family: 'Roboto Mono', monospace; font-size: 100px; font-weight: 700;
        color: #FFFFFF; text-shadow: 0 0 25px rgba(59, 130, 246, 0.5);
    }

    /* PERFIL LATERAL */
    .profile-box { text-align: center; margin-bottom: 30px; margin-top: 10px; }
    .profile-dev { font-size: 12px; color: #9CA3AF; margin-bottom: 2px; }
    .profile-name { font-weight: 700; font-size: 20px; color: #FFFFFF; }
    
    /* BOTÃO SPARKLE */
    .stButton>button { border-radius: 12px; font-weight: 600; border: none; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. GESTÃO DE ESTADO
# =============================================================================
DEFAULTS = {
    "user_xp": 0, "user_level": 1,
    "edital_text": "", 
    "chat_history": [], # Histórico do Modo Estudo
    "generated_questions": [], 
    "lgpd_ack": False, "last_heavy_call": 0.0,
    # Pomodoro
    "pomo_state": "STOPPED", "pomo_mode": "Foco", 
    "pomo_duration": 25 * 60, "pomo_end_time": None, "pomo_auto_start": False
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

RATE_LIMIT_SECONDS = 2

def check_rate_limit():
    now = time.time()
    if now - st.session_state.last_heavy_call < RATE_LIMIT_SECONDS:
        return True
    return False

def mark_call():
    st.session_state.last_heavy_call = time.time()

def extract_json_safe(text):
    match = re.search(r"<json>(.*?)</json>", text, re.DOTALL)
    json_str = match.group(1) if match else None
    if not json_str:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        json_str = match.group(0) if match else None
    if json_str:
        try: return json.loads(json_str)
        except: return None
    return None

# =============================================================================
# 3. MOTOR DE IA (GROQ)
# =============================================================================
def get_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return None
    return Groq(api_key=api_key)

def stream_text(text):
    """Simula digitação (efeito Gemini)"""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)

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
# 4. SIDEBAR (CLEAN)
# =============================================================================
with st.sidebar:
    try: st.image("logo.jpg.png", use_container_width=True)
    except: pass
    
    st.markdown("---")
    
    # Menu com Ícones
    menu = st.radio("Menu:", 
        ["✨ Estudo Gemini", "🍅 Sala de Foco", "📄 Redação", "🏢 Cartório OCR", "🎙️ Transcrição"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    c_link, c_zap = st.columns(2)
    with c_link: st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")
    with c_zap: st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720)")

    st.markdown("""
    <div style="text-align: center; margin-top: 20px; color: #6B7280; font-size: 12px;">
        Desenvolvido por <br><strong style="color: #E5E7EB;">Arthur Carmélio</strong>
    </div>
    """, unsafe_allow_html=True)

# LGPD
if not st.session_state.lgpd_ack:
    with st.expander("🔐 Acesso ao Sistema", expanded=True):
        st.write("Ao entrar, você concorda com o uso de IA.")
        if st.button("Entrar"):
            st.session_state.lgpd_ack = True
            st.rerun()
    st.stop()

# =============================================================================
# 5. MÓDULOS (GEMINI MODE)
# =============================================================================

# --- MODO ESTUDO GEMINI (PRINCIPAL) ---
if menu == "✨ Estudo Gemini":
    # Header com Gradiente
    st.markdown('<h1 class="gemini-text">Olá, Arthur</h1>', unsafe_allow_html=True)
    st.caption("Sou sua Inteligência Artificial Jurídica. Suba um edital ou peça uma questão para começar.")

    # 1. Área de Contexto (Edital) - Discreto no topo
    with st.expander("📂 Contexto do Estudo (Edital/PDF)", expanded=not bool(st.session_state.edital_text)):
        file = st.file_uploader("Arraste seu documento aqui", type=["pdf", "docx"])
        if file:
            with st.spinner("Analisando documento..."):
                raw = "Conteúdo..."
                if file.type == "application/pdf" and pdfplumber:
                    with pdfplumber.open(BytesIO(file.getvalue())) as pdf: raw = "".join([p.extract_text() or "" for p in pdf.pages])
                elif "word" in file.type and docx_reader:
                    doc = docx_reader.Document(BytesIO(file.getvalue()))
                    raw = "\n".join([p.text for p in doc.paragraphs])
                
                st.session_state.edital_text = raw
                # Adiciona mensagem de sistema ao chat se for novo
                st.session_state.chat_history.append({"role": "assistant", "content": f"✅ **Edital '{file.name}' processado!** Agora posso criar questões específicas sobre ele. O que deseja treinar?"})
                st.rerun()

    # 2. Histórico de Chat (Interface Principal)
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            # Se for JSON de questão, renderiza bonito
            if isinstance(msg["content"], dict) and "enunciado" in msg["content"]:
                q = msg["content"]
                st.markdown(f"<div class='question-card'><strong>QUESTÃO INÉDITA</strong><br><br>{q['enunciado']}</div>", unsafe_allow_html=True)
                for k,v in q["alternativas"].items():
                    st.write(f"**{k})** {v}")
                with st.expander("👁️ Ver Gabarito"):
                    st.success(f"**{q['gabarito']}**")
                    st.info(q['comentario'])
            else:
                st.markdown(msg["content"])

    # 3. Controles de Geração (Abaixo do chat para facilitar)
    st.markdown("---")
    c1, c2, c3 = st.columns([2, 1, 1])
    
    # Input de Texto Livre
    if prompt := st.chat_input("Ex: Me explique Dolo Eventual ou gere uma questão sobre isso..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                # Decide se é comando de questão ou chat normal
                if "questão" in prompt.lower() or "exercício" in prompt.lower():
                    ctx = st.session_state.edital_text[:3000] if st.session_state.edital_text else ""
                    sys_p = f"Você é um examinador de banca. Contexto: {ctx}. Retorne JSON <json>...</json>."
                    res = call_ai(prompt, system=sys_p, temp=0.5)
                    data = extract_json_safe(res)
                    if data:
                        st.session_state.chat_history.append({"role": "assistant", "content": data})
                        st.rerun()
                    else:
                        st.write(res)
                        st.session_state.chat_history.append({"role": "assistant", "content": res})
                else:
                    res = call_ai(prompt, system="Seja um mentor jurídico didático.")
                    st.write_stream(stream_text(res))
                    st.session_state.chat_history.append({"role": "assistant", "content": res})

    # Botões Rápidos (Chips)
    st.write("Sugestões:")
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("🎲 Questão Aleatória"):
        st.session_state.chat_history.append({"role": "user", "content": "Gere uma questão difícil aleatória de Direito."})
        st.rerun()
    if b2.button("🎯 Questão do Edital", disabled=not st.session_state.edital_text):
        st.session_state.chat_history.append({"role": "user", "content": "Gere uma questão baseada no edital carregado."})
        st.rerun()
    if b3.button("🧹 Limpar Chat"):
        st.session_state.chat_history = []
        st.rerun()

# --- SALA DE FOCO ---
elif menu == "🍅 Sala de Foco":
    st.title("🍅 Foco & Produtividade")
    
    col_modes = st.columns([1,1,1])
    def set_pomo(mode, min):
        st.session_state.pomo_mode = mode
        st.session_state.pomo_duration = min * 60
        st.session_state.pomo_state = "STOPPED"
        st.session_state.pomo_end_time = None
        st.rerun()

    if col_modes[0].button("🧠 FOCO (25m)", use_container_width=True): set_pomo("Foco", 25)
    if col_modes[1].button("☕ CURTO (5m)", use_container_width=True): set_pomo("Descanso", 5)
    if col_modes[2].button("🧘 LONGO (15m)", use_container_width=True): set_pomo("Longo", 15)

    remaining = st.session_state.pomo_duration
    if st.session_state.pomo_state == "RUNNING":
        now = time.time()
        if now >= st.session_state.pomo_end_time:
            st.session_state.pomo_state = "STOPPED"
            st.balloons()
            st.markdown("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", unsafe_allow_html=True)
            
            if st.session_state.pomo_auto_start:
                next_mode = "Descanso" if st.session_state.pomo_mode == "Foco" else "Foco"
                next_min = 5 if next_mode == "Descanso" else 25
                st.session_state.pomo_mode = next_mode
                st.session_state.pomo_duration = next_min * 60
                st.session_state.pomo_end_time = time.time() + (next_min * 60)
                st.session_state.pomo_state = "RUNNING"
                time.sleep(2)
                st.rerun()
            else:
                remaining = 0
        else:
            remaining = int(st.session_state.pomo_end_time - now)
            time.sleep(1)
            st.rerun()

    mins, secs = divmod(remaining, 60)
    
    st.markdown(f"""
    <div class="timer-container">
        <div style="color: #60A5FA; letter-spacing: 3px; margin-bottom: 10px;">{st.session_state.pomo_mode.upper()}</div>
        <div class="timer-display">{mins:02d}:{secs:02d}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    if c1.button("▶️ INICIAR", use_container_width=True, type="primary"):
        if st.session_state.pomo_state != "RUNNING":
            st.session_state.pomo_state = "RUNNING"
            st.session_state.pomo_end_time = time.time() + remaining
            st.rerun()
    if c2.button("⏸️ PAUSAR", use_container_width=True):
        if st.session_state.pomo_state == "RUNNING":
            st.session_state.pomo_state = "PAUSED"
            st.session_state.pomo_duration = remaining
            st.rerun()
    if c3.button("🔄 ZERAR", use_container_width=True):
        st.session_state.pomo_state = "STOPPED"
        st.session_state.pomo_duration = 25 * 60
        st.rerun()

    st.session_state.pomo_auto_start = st.checkbox("🔄 Ciclos automáticos", value=st.session_state.pomo_auto_start)
    with st.expander("🎵 Rádio Lofi", expanded=False):
        st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")

# --- REDAÇÃO ---
elif menu == "📄 Redação":
    st.title("📄 Redação Jurídica")
    st.info("Descreva o caso e a IA redige a peça para você.")
    
    c1, c2 = st.columns([1, 2])
    tipo = c1.selectbox("Tipo", ["Petição Inicial", "Contestação", "Contrato", "Procuração", "Habeas Corpus"])
    det = c2.text_area("Fatos e Detalhes", height=100)
    
    if st.button("✍️ Gerar Minuta"):
        with st.spinner("Escrevendo..."):
            res = call_ai(f"Redija um(a) {tipo}. Fatos: {det}. Linguagem técnica.", temp=0.2)
            st.text_area("Minuta:", res, height=500)

# --- OCR ---
elif menu == "🏢 Cartório OCR":
    st.title("🏢 Leitor de Documentos")
    st.info("Extraia texto de imagens e PDFs.")
    u = st.file_uploader("Arquivo", type=["jpg","png","pdf"])
    if u and st.button("Extrair"):
        with st.spinner("Processando..."):
            res = call_ai("Transcreva fielmente.", file_bytes=u.getvalue(), type="vision")
            st.text_area("Texto:", res, height=400)

# --- TRANSCRIÇÃO ---
elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição")
    st.info("Grave áudios e converta em texto.")
    a = st.audio_input("Gravar")
    if a:
        with st.spinner("Transcrevendo..."):
            res = call_ai("", file_bytes=a.getvalue(), type="audio")
            st.success("Texto:")
            st.write(res)
