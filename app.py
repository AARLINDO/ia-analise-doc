import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIGURAÇÃO E CSS (A Mágica Visual) ---
st.set_page_config(
    page_title="Carmélio AI",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed" # Começa fechado pra dar foco total
)

st.markdown("""
<style>
    /* 1. Limpeza Geral */
    .stDeployButton, footer, header {display:none !important;}
    div[data-testid="stToolbar"] {display: none !important;}
    
    /* 2. Centralizar a Tela de Boas-Vindas */
    .welcome-container {
        text-align: center;
        margin-top: 10vh;
        animation: fadeIn 1.5s ease-in-out;
    }
    .welcome-title {
        font-size: 3rem;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #4285F4, #9B72CB);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .welcome-subtitle {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 30px;
    }
    
    /* 3. Cards de Sugestão (Estilo Gemini) */
    .suggestion-grid {
        display: flex;
        gap: 15px;
        justify-content: center;
        flex-wrap: wrap;
    }
    .suggestion-card {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px 20px;
        width: 200px;
        cursor: pointer;
        transition: all 0.2s;
        text-align: left;
        font-size: 0.9rem;
        color: #444;
    }
    .suggestion-card:hover {
        background-color: #e8f0fe;
        border-color: #4285F4;
        transform: translateY(-2px);
    }

    /* 4. POSICIONAMENTO DO INPUT (O Segredo) */
    /* Fixa o Microfone flutuando acima da barra de texto */
    div[data-testid="stAudioInput"] {
        position: fixed;
        bottom: 80px; /* Logo acima do chat input */
        left: 50%;
        transform: translateX(-50%);
        width: 60% !important; /* Largura centralizada */
        z-index: 1000;
        background: transparent;
    }
    
    /* Estiliza o Chat Input para ficar fixo no fundo */
    .stChatInput {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        padding-bottom: 20px;
        padding-top: 10px;
        background: white; /* Fundo branco pra esconder o scroll */
        z-index: 999;
    }
    
    /* 5. Ajuste das Mensagens */
    .stChatMessage {
        max-width: 800px;
        margin: 0 auto; /* Centraliza o chat na tela */
    }
    
    @keyframes fadeIn {
        0% { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

# --- 2. ESTADO E FUNÇÕES ---
if "history" not in st.session_state: st.session_state.history = []
if "file" not in st.session_state: st.session_state.file = None

def gerar_word(texto):
    try:
        doc = Document()
        doc.add_heading('Resposta Carmélio AI', 0)
        for p in texto.split('\n'):
            if p.strip(): doc.add_paragraph(p)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except: return None

def upload_handler(up):
    try:
        ext = os.path.splitext(up.name)[1]
        mime = mimetypes.guess_type(up.name)[0] or 'application/octet-stream'
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(up.getvalue()); tmp_path = tmp.name
        ref = genai.upload_file(path=tmp_path, mime_type=mime, display_name="UserFile")
        while ref.state.name == "PROCESSING": time.sleep(1); ref = genai.get_file(ref.name)
        return ref
    except: return None

# --- 3. BARRA LATERAL (Discreta) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Google_Chrome_icon_%28February_2022%29.svg/800px-Google_Chrome_icon_%28February_2022%29.svg.png", width=50)
    st.markdown("### ⚙️ Configurações")
    
    # Upload aqui para não sujar a tela principal
    with st.expander("📂 Anexar Arquivo", expanded=True):
        up = st.file_uploader("PDF, Áudio, Imagem", label_visibility="collapsed")
        if up:
            with st.spinner("Enviando..."):
                ref = upload_handler(up)
                if ref:
                    st.session_state.file = ref
                    st.success("Arquivo Anexado!")

    if st.button("🗑️ Limpar Conversa"):
        st.session_state.history = []
        st.session_state.file = None
        st.rerun()

# --- 4. TELA PRINCIPAL (LÓGICA GEMINI) ---

# A) Se não tem mensagens, mostra a tela de Boas-Vindas (Gemini Style)
if not st.session_state.history:
    st.markdown(f"""
    <div class="welcome-container">
        <div class="welcome-title">Olá, Arthur</div>
        <div class="welcome-subtitle">Como posso ajudar você hoje com seus processos e estudos?</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Grid de Sugestões (Botões invisíveis que acionam prompts)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 Criar Petição Inicial\n(Cobrança Indevida)", use_container_width=True):
            prompt_inicial = "Crie uma petição inicial de cobrança indevida."
            st.session_state.history.append({"role": "user", "content": prompt_inicial})
            st.rerun()
    with col2:
        if st.button("📅 Resumir Prazos\n(Analisar Edital)", use_container_width=True):
            prompt_inicial = "Quais são os prazos deste documento?"
            st.session_state.history.append({"role": "user", "content": prompt_inicial})
            st.rerun()
    with col3:
        if st.button("⚖️ Analisar Riscos\n(Contrato de Locação)", use_container_width=True):
            prompt_inicial = "Analise os riscos jurídicos."
            st.session_state.history.append({"role": "user", "content": prompt_inicial})
            st.rerun()

# B) Se tem mensagens, mostra o chat (com padding no fundo pra não cobrir)
else:
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and len(msg["content"]) > 100:
                docx = gerar_word(msg["content"])
                if docx: st.download_button("⬇️ Word", docx, file_name="Analise.docx", key=f"d_{hash(msg['content'])}")
    
    # Espaço vazio no fim para o scroll não ficar preso embaixo do input
    st.markdown("<div style='height: 150px;'></div>", unsafe_allow_html=True)

# --- 5. ÁREA DE INPUT (FIXA NO RODAPÉ) ---

# O Microfone fica flutuando (veja o CSS lá em cima)
audio_val = st.audio_input("Falar", label_visibility="collapsed")

# O Chat Input fica fixo no fundo
prompt_val = st.chat_input("Digite uma mensagem ou comando...")

# LÓGICA DE ENVIO
if prompt_val or audio_val:
    user_msg = prompt_val if prompt_val else "🎤 [Áudio Enviado]"
    st.session_state.history.append({"role": "user", "content": user_msg})
    
    # Processamento IA
    with st.spinner("✨ Pensando..."):
        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            hist_api = []
            # Injeta Arquivo se existir
            if st.session_state.file:
                hist_api.append({"role": "user", "parts": [st.session_state.file, "Contexto."]})
                hist_api.append({"role": "model", "parts": ["Ok."]})
            
            # Injeta Áudio Novo se existir
            if audio_val:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as t:
                    t.write(audio_val.getvalue()); tpath = t.name
                ref_mic = genai.upload_file(path=tpath, mime_type="audio/wav")
                while ref_mic.state.name == "PROCESSING": time.sleep(0.5); ref_mic = genai.get_file(ref_mic.name)
                hist_api.append({"role": "user", "parts": [ref_mic, "Transcreva e responda."]})
                hist_api.append({"role": "model", "parts": ["Ok."]})

            # Histórico
            for m in st.session_state.history:
                if m["content"] != "🎤 [Áudio Enviado]": # Evita duplicar placeholder
                    role = "model" if m["role"] == "assistant" else "user"
                    hist_api.append({"role": role, "parts": [m["content"]]})

            prompt_final = prompt_val if prompt_val else "Analise o áudio enviado."
            
            chat = model.start_chat(history=hist_api)
            response = chat.send_message(prompt_final)
            st.session_state.history.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Erro: {e}")
    
    st.rerun()
