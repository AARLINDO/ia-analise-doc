import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
import mimetypes
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIGURAÇÃO DE UI (GEMINI DARK MODE) ---
st.set_page_config(
    page_title="Carmélio AI",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS AVANÇADO (A MÁGICA VISUAL) ---
st.markdown("""
<style>
    /* FUNDO E CORES GERAIS (Paleta Gemini Dark) */
    .stApp {
        background-color: #131314; /* Cinza Gemini */
        color: #E3E3E3;
    }
    
    /* ESCONDER ELEMENTOS PADRÃO */
    header, footer, .stDeployButton {display: none !important;}
    div[data-testid="stToolbar"] {display: none !important;}
    
    /* BARRA LATERAL */
    section[data-testid="stSidebar"] {
        background-color: #1E1F20;
        border-right: 1px solid #333;
    }
    
    /* TEXTO DE BOAS-VINDAS (GRADIENTE) */
    .hero-container {
        padding-top: 10vh;
        padding-bottom: 40px;
        max-width: 800px;
        margin: 0 auto;
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 600;
        background: linear-gradient(90deg, #4285F4, #9B72CB, #D96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }
    .hero-subtitle {
        font-size: 1.5rem;
        color: #444746; /* Cinza Google */
        font-weight: 500;
    }
    
    /* CARTÕES DE SUGESTÃO */
    .card-container {
        display: flex;
        gap: 15px;
        overflow-x: auto;
        padding-bottom: 20px;
        margin-bottom: 50px;
    }
    /* Estilizando os botões nativos para parecerem cards */
    .stButton button {
        background-color: #1E1F20 !important;
        border: 1px solid #444 !important;
        color: #E3E3E3 !important;
        border-radius: 12px !important;
        height: 100px !important;
        white-space: pre-wrap !important; /* Permite quebra de linha */
        text-align: left !important;
        transition: 0.3s;
    }
    .stButton button:hover {
        background-color: #2D2E2F !important;
        border-color: #A8C7FA !important;
    }

    /* INPUT AREA (O "Dock" no fundo) */
    .stChatInput {
        position: fixed;
        bottom: 0px;
        background-color: #131314;
        padding-bottom: 20px;
        padding-top: 10px;
        z-index: 999;
    }
    
    /* ÁUDIO INPUT FLUTUANTE */
    div[data-testid="stAudioInput"] {
        position: fixed;
        bottom: 85px; /* Logo acima do texto */
        left: 50%;
        transform: translateX(-50%);
        width: 50%;
        max-width: 600px;
        background-color: #1E1F20;
        border-radius: 30px;
        padding: 5px;
        border: 1px solid #444;
        z-index: 1000;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    /* Remove bordas feias do audio */
    div[data-testid="stAudioInput"] > div {
        border: none !important;
        background: transparent !important;
    }

    /* MENSAGENS DO CHAT */
    .stChatMessage {
        background-color: transparent !important;
    }
    div[data-testid="stChatMessageAvatarUser"] {
        background-color: #A8C7FA !important; /* Azul Google User */
        color: black !important;
    }
    div[data-testid="stChatMessageAvatarAssistant"] {
        background-color: transparent !important;
        border: 1px solid #444;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. LÓGICA DE BACKEND ---
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
        ref = genai.upload_file(path=tmp_path, mime_type=mime, display_name="ArquivoUsuario")
        while ref.state.name == "PROCESSING": time.sleep(0.5); ref = genai.get_file(ref.name)
        return ref
    except: return None

# --- 4. BARRA LATERAL (MENU HAMBURGUER) ---
with st.sidebar:
    st.markdown("### ≡ Menu")
    
    # Upload Discreto
    with st.expander("📂 Adicionar Contexto (PDF/Áudio)", expanded=False):
        uploaded = st.file_uploader("Arquivo", label_visibility="collapsed")
        if uploaded:
            with st.spinner("Anexando..."):
                ref = upload_handler(uploaded)
                if ref:
                    st.session_state.file = ref
                    st.toast("Arquivo anexado à memória!", icon="🧠")

    st.markdown("---")
    if st.button("🗑️ Nova Conversa / Limpar"):
        st.session_state.history = []
        st.session_state.file = None
        st.rerun()

# --- 5. TELA PRINCIPAL ---

# TELA 1: BOAS VINDAS (QUANDO VAZIO)
if not st.session_state.history:
    # Saudação baseada no horário
    hora = datetime.now().hour
    saudacao = "Bom dia" if 5 <= hora < 12 else "Boa tarde" if 12 <= hora < 18 else "Boa noite"
    
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-title">Olá, Arthur</div>
        <div class="hero-subtitle">{saudacao}. O que vamos analisar hoje?</div>
    </div>
    """, unsafe_allow_html=True)

    # Grid de Sugestões (Usando colunas do Streamlit para layout)
    c1, c2, c3, c4 = st.columns(4)
    
    prompt_selecionado = None
    
    with c1:
        if st.button("📝 Resumir\nProcesso", use_container_width=True):
            prompt_selecionado = "Faça um resumo processual detalhado deste caso."
    with c2:
        if st.button("💡 Criar Tese\nde Defesa", use_container_width=True):
            prompt_selecionado = "Crie uma tese de defesa baseada na jurisprudência atual."
    with c3:
        if st.button("📅 Calcular\nPrazos", use_container_width=True):
            prompt_selecionado = "Identifique todas as datas e prazos processuais."
    with c4:
        if st.button("📧 E-mail para\nCliente", use_container_width=True):
            prompt_selecionado = "Escreva um e-mail formal explicando a situação para o cliente."

    if prompt_selecionado:
        st.session_state.history.append({"role": "user", "content": prompt_selecionado})
        st.rerun()

# TELA 2: CHAT ATIVO
else:
    # Container para centralizar o chat (largura máxima de leitura)
    with st.container():
        for msg in st.session_state.history:
            if msg["content"] == "🎤 [Áudio Enviado]": continue # Pula placeholder visual
            
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # Botão Word (Sutil e elegante)
                if msg["role"] == "assistant" and len(msg["content"]) > 100:
                    docx = gerar_word(msg["content"])
                    if docx:
                        st.download_button("📄 Exportar DOCX", docx, file_name="Carmelio_Doc.docx", key=f"d_{hash(msg['content'])}")
    
    # Espaço para o scroll não bater no input fixo
    st.markdown("<div style='height: 180px;'></div>", unsafe_allow_html=True)


# --- 6. BARRA DE COMANDOS (FIXA NO FUNDO) ---

# Microfone (Flutuante acima do texto)
audio_val = st.audio_input("Voz", label_visibility="collapsed")

# Texto (Fixo no rodapé)
if st.session_state.file:
    placeholder = f"Pergunte sobre {st.session_state.file.display_name}..."
else:
    placeholder = "Digite uma mensagem, peça uma petição ou análise..."

prompt_val = st.chat_input(placeholder)

# LÓGICA DE ENVIO UNIFICADA
if prompt_val or audio_val:
    # Define o conteúdo do usuário
    user_content = prompt_val if prompt_val else "🎤 [Áudio Enviado]"
    
    # Adiciona ao histórico visual
    st.session_state.history.append({"role": "user", "content": user_content})
    
    # Processamento IA
    with st.spinner("✨ Carmélio AI processando..."):
        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            hist_api = []
            
            # Contexto do Arquivo
            if st.session_state.file:
                hist_api.append({"role": "user", "parts": [st.session_state.file, "Contexto do arquivo."]})
                hist_api.append({"role": "model", "parts": ["Entendido."]})
            
            # Contexto do Áudio Novo
            if audio_val:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as t:
                    t.write(audio_val.getvalue()); tpath = t.name
                ref_mic = genai.upload_file(path=tpath, mime_type="audio/wav")
                while ref_mic.state.name == "PROCESSING": time.sleep(0.5); ref_mic = genai.get_file(ref_mic.name)
                hist_api.append({"role": "user", "parts": [ref_mic, "Transcreva e responda."]})
                hist_api.append({"role": "model", "parts": ["Áudio recebido."]})
                os.remove(tpath)

            # Histórico de Conversa
            for m in st.session_state.history:
                if "🎤" not in m["content"]: # Evita mandar lixo pro modelo
                    role = "model" if m["role"] == "assistant" else "user"
                    hist_api.append({"role": role, "parts": [m["content"]]})

            prompt_final = prompt_val if prompt_val else "Analise o áudio enviado."
            
            chat = model.start_chat(history=hist_api)
            response = chat.send_message(prompt_final)
            
            st.session_state.history.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Erro: {e}")
            
    st.rerun()
