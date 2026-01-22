import streamlit as st
from groq import Groq
from docx import Document
from io import BytesIO
from datetime import datetime
import json
import base64
import time
import re
import os

# =============================================================================
# 1. CONFIGURAÇÃO E DESIGN
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Suíte Jurídica",
    page_icon="✨",
    layout="wide"
)

# Importações seguras (Evita erro se faltar lib)
try: import pdfplumber
except ImportError: pdfplumber = None
try: import docx as docx_reader
except ImportError: docx_reader = None
try: from PIL import Image
except ImportError: Image = None

st.markdown("""
<style>
    /* GERAL */
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    
    /* TEXTO GEMINI */
    .gemini-text {
        background: -webkit-linear-gradient(45deg, #4285F4, #9B72CB, #D96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.2rem; margin-bottom: 10px;
    }
    
    /* POMODORO */
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@700&display=swap');
    .timer-display {
        font-family: 'Roboto Mono', monospace; font-size: 100px; font-weight: 700;
        color: #FFFFFF; text-shadow: 0 0 25px rgba(59, 130, 246, 0.5);
    }
    .timer-container {
        background-color: #1F2430; border-radius: 20px; padding: 30px;
        text-align: center; border: 1px solid #2B2F3B; margin: 20px auto;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 600px;
    }

    /* RODAPÉ E CRÉDITOS */
    .footer-credits {
        text-align: center; margin-top: 40px; padding-top: 20px;
        border-top: 1px solid #2B2F3B; color: #6B7280; font-size: 12px;
    }
    .footer-name {
        color: #E5E7EB; font-weight: 700; font-size: 14px; display: block; margin-top: 5px;
    }
    
    /* BOTÕES E INPUTS */
    .stButton>button { border-radius: 12px; font-weight: 600; border: none; }
    .stChatInput { border-radius: 20px; border: 1px solid #374151; }
    .question-card { 
        background: linear-gradient(135deg, #1F2937 0%, #111827 100%); 
        padding: 20px; border-radius: 15px; border: 1px solid #374151; margin-bottom: 10px; 
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. GESTÃO DE ESTADO
# =============================================================================
# Inicializa variáveis se não existirem
DEFAULTS = {
    "edital_text": "", 
    "chat_history": [], 
    "generated_questions": [], 
    "lgpd_ack": False, 
    "last_heavy_call": 0.0,
    # Pomodoro
    "pomo_state": "STOPPED", 
    "pomo_mode": "Foco", 
    "pomo_duration": 25 * 60, 
    "pomo_end_time": None,
    # Atenção: pomo_auto_start é gerenciado pelo widget key, não precisa default aqui se usar key
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
# 3. MOTOR DE IA
# =============================================================================
def get_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return None
    return Groq(api_key=api_key)

def stream_text(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)

def call_ai(messages_or_prompt, file_bytes=None, type="text", system="Você é o Carmélio AI, assistente jurídico.", temp=0.5):
    if check_rate_limit(): return None
    client = get_client()
    if not client: return "⚠️ Configure a GROQ_API_KEY."
    
    mark_call()
    try:
        if type == "text":
            if isinstance(messages_or_prompt, str):
                msgs = [{"role":"system","content":system}, {"role":"user","content":messages_or_prompt}]
            else:
                msgs = [{"role":"system","content":system}] + messages_or_prompt

            r = client.chat.completions.create(
                messages=msgs, model="llama-3.3-70b-versatile", temperature=temp
            )
            return r.choices[0].message.content
            
        elif type == "vision" and file_bytes:
            b64 = base64.b64encode(file_bytes).decode('utf-8')
            r = client.chat.completions.create(
                messages=[{"role":"user","content":[{"type":"text","text":messages_or_prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}],
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
# 4. SIDEBAR
# =============================================================================
with st.sidebar:
    # 1. LOGO (Com Fallback para evitar erro)
    if os.path.exists("logo.jpg.png"):
        try:
            st.image("logo.jpg.png", use_container_width=True)
        except TypeError:
            # Fallback para versões antigas do Streamlit
            st.image("logo.jpg.png", use_column_width=True)
    else:
        st.warning("⚠️ logo.jpg.png não encontrada")
    
    st.markdown("---")
    
    # 2. MENU
    menu = st.radio("Menu Principal:", 
        ["✨ Chat Inteligente", "🎯 Mestre dos Editais", "🍅 Sala de Foco", "📄 Redação Jurídica", "🏢 Cartório OCR", "🎙️ Transcrição"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 3. LINKS
    c_link, c_zap = st.columns(2)
    with c_link: st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")
    with c_zap: st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720)")

    # 4. CRÉDITOS
    st.markdown("""
    <div class="footer-credits">
        Desenvolvido por <br>
        <span class="footer-name">Arthur Carmélio</span>
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
# 5. MÓDULOS
# =============================================================================

# --- 1. CHAT INTELIGENTE (HOME) ---
if menu == "✨ Chat Inteligente":
    st.markdown('<h1 class="gemini-text">Olá, Doutor(a).</h1>', unsafe_allow_html=True)
    
    if not st.session_state.chat_history:
        st.caption("Sou o Carmélio AI. Posso ajudar com dúvidas, peças, estudos ou jurisprudência.")
        c1, c2 = st.columns(2)
        if c1.button("📚 Explicar Conceito"):
            st.session_state.chat_history.append({"role": "user", "content": "Explique a diferença entre Prescrição e Decadência."})
            st.rerun()
        if c2.button("💡 Ideias de Tese"):
            st.session_state.chat_history.append({"role": "user", "content": "Sugira teses de defesa para crime de furto famélico."})
            st.rerun()

    # Histórico
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Digite sua mensagem..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                context_msgs = st.session_state.chat_history[-6:]
                res = call_ai(context_msgs, system="Seja um mentor jurídico preciso.")
                st.write_stream(stream_text(res))
                st.session_state.chat_history.append({"role": "assistant", "content": res})

    if st.session_state.chat_history:
        if st.button("🗑️ Limpar Conversa"):
            st.session_state.chat_history = []
            st.rerun()

# --- 2. MESTRE DOS EDITAIS ---
elif menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais")
    
    with st.expander("📂 Upload do Edital (Contexto)", expanded=not bool(st.session_state.edital_text)):
        file = st.file_uploader("Arraste seu PDF/DOCX", type=["pdf", "docx"])
        if file:
            with st.spinner("Lendo edital..."):
                raw = "Conteúdo..."
                if file.type == "application/pdf" and pdfplumber:
                    with pdfplumber.open(BytesIO(file.getvalue())) as pdf: raw = "".join([p.extract_text() or "" for p in pdf.pages])
                elif "word" in file.type and docx_reader:
                    doc = docx_reader.Document(BytesIO(file.getvalue()))
                    raw = "\n".join([p.text for p in doc.paragraphs])
                st.session_state.edital_text = raw
                st.success("Edital carregado! A IA usará este contexto.")
                st.rerun()

    st.markdown("---")
    
    c1, c2, c3 = st.columns(3)
    banca = c1.selectbox("Banca", ["FGV", "Cebraspe", "Vunesp", "FCC"])
    disc = c2.selectbox("Disciplina", ["Constitucional", "Administrativo", "Penal", "Civil"])
    assunto = c3.text_input("Assunto", "Atos Administrativos")

    if st.button("🚀 Gerar Questão Inédita", type="primary", use_container_width=True):
        with st.spinner("Criando..."):
            ctx = st.session_state.edital_text[:3000] if st.session_state.edital_text else ""
            p = f"Crie uma questão inédita (JSON). Banca: {banca}. Disciplina: {disc}. Assunto: {assunto}. Contexto Edital: {ctx}. Formato: <json>{{'enunciado':'...', 'alternativas':{{'A':'...','B':'...'}}, 'gabarito':'A', 'comentario':'...'}}</json>"
            res = call_ai(p, temp=0.5)
            data = extract_json_safe(res)
            
            if data:
                st.session_state.generated_questions.append(data)
    
    if st.session_state.generated_questions:
        q = st.session_state.generated_questions[-1]
        st.markdown(f"<div class='question-card'><strong>{banca} | {disc}</strong><br><br>{q.get('enunciado')}</div>", unsafe_allow_html=True)
        for k,v in q.get("alternativas", {}).items():
            st.write(f"**{k})** {v}")
        with st.expander("Ver Gabarito"):
            st.success(f"Gabarito: {q.get('gabarito')}")
            st.info(q.get("comentario"))

# --- 3. SALA DE FOCO ---
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
            
            # Verifica se o checkbox de auto-start está marcado (usando get para evitar erro)
            if st.session_state.get("pomo_auto_start"):
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

    # Correção do SyntaxError: Checkbox apenas com key
    st.checkbox("🔄 Ciclos automáticos", key="pomo_auto_start")
    
    with st.expander("🎵 Rádio Lofi", expanded=False):
        st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")

# --- 4. REDAÇÃO ---
elif menu == "📄 Redação Jurídica":
    st.title("📄 Redação Jurídica")
    st.info("Descreva o caso e a IA redige a peça para você.")
    
    c1, c2 = st.columns([1, 2])
    tipo = c1.selectbox("Tipo", ["Petição Inicial", "Contestação", "Contrato", "Procuração", "Habeas Corpus"])
    det = c2.text_area("Fatos e Detalhes", height=100)
    
    if st.button("✍️ Gerar Minuta"):
        with st.spinner("Escrevendo..."):
            res = call_ai(f"Redija um(a) {tipo}. Fatos: {det}. Linguagem técnica.", temp=0.2)
            st.text_area("Minuta:", res, height=500)

# --- 5. OCR ---
elif menu == "🏢 Cartório OCR":
    st.title("🏢 Leitor de Documentos")
    st.info("Extraia texto de imagens e PDFs.")
    u = st.file_uploader("Arquivo", type=["jpg","png","pdf"])
    if u and st.button("Extrair"):
        with st.spinner("Processando..."):
            res = call_ai("Transcreva fielmente.", file_bytes=u.getvalue(), type="vision")
            st.text_area("Texto:", res, height=400)

# --- 6. TRANSCRIÇÃO (COM FALLBACK) ---
elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição")
    st.info("Grave áudios e converta em texto.")
    
    # Tratamento para evitar AttributeError em versões antigas
    audio_file = None
    try:
        audio_file = st.audio_input("Gravar")
    except AttributeError:
        st.warning("⚠️ Seu sistema não suporta gravação direta. Use o upload abaixo.")
        audio_file = st.file_uploader("Upload de Áudio", type=["wav", "mp3", "m4a"])

    if audio_file:
        # Se for st.audio_input (retorna objeto) ou file_uploader (retorna objeto)
        # O método getvalue() funciona em ambos
        if st.button("Transcrever"):
            with st.spinner("Transcrevendo..."):
                res = call_ai("", file_bytes=audio_file.getvalue(), type="audio")
                st.success("Texto:")
                st.write(res)
