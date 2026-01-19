import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO INICIAL E CSS ---
st.set_page_config(
    page_title="Carmélio AI - Suite Jurídica",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS Profissional
st.markdown("""
<style>
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .login-container {
        margin-top: 100px;
        padding: 40px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stButton button {
        width: 100%;
        border-radius: 8px;
        text-align: left;
        padding-left: 15px;
    }
    /* Destaque para mensagem do sistema */
    .stChatMessage {
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. GERENCIAMENTO DE ESTADO ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "chats" not in st.session_state:
    st.session_state.chats = {
        "chat_1": {"title": "Nova Conversa", "history": [], "file": None, "file_type": None}
    }
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = "chat_1"
if "mode" not in st.session_state:
    st.session_state.mode = "Análise de Arquivos"

# --- 3. FUNÇÕES AUXILIARES ---
def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='text-align: center;'><h1>⚖️ Carmélio AI</h1><p>Suite Jurídica Multimodal</p></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        usuario = st.text_input("Usuário:")
        senha_digitada = st.text_input("Senha:", type="password")
        
        if st.button("Acessar Sistema", type="primary"):
            usuarios_cadastrados = st.secrets.get("passwords", {})
            if usuario in usuarios_cadastrados and usuarios_cadastrados[usuario] == senha_digitada:
                st.session_state.logged_in = True
                st.session_state.username = usuario
                st.toast(f"Bem-vindo, {usuario}!", icon="🔓")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("🔒 Credenciais inválidas.")

def create_new_chat():
    new_id = f"chat_{len(st.session_state.chats) + 1}"
    st.session_state.chats[new_id] = {
        "title": f"Conversa {len(st.session_state.chats) + 1}", 
        "history": [], 
        "file": None,
        "file_type": None
    }
    st.session_state.current_chat_id = new_id
    st.rerun()

def delete_chat(chat_id):
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[chat_id]
        st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
        st.rerun()

def sidebar_menu():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.get('username', 'Usuário')}")
        
        # --- SELETOR DE MODO ---
        st.session_state.mode = st.radio(
            "Modo de Operação:",
            ["Análise de Arquivos", "Chat Jurídico (Livre)"],
            captions=["PDF, Áudio, Imagens", "Consultoria sem arquivos"]
        )
        st.markdown("---")
        
        st.markdown("### 🗂️ Histórico")
        if st.button("➕ Nova Conversa", type="primary"):
            create_new_chat()
        
        st.markdown("---")
        
        # Lista de Chats
        for chat_id, chat_data in list(st.session_state.chats.items())[::-1]: # Inverte para o mais novo ficar em cima
            label = chat_data["title"]
            if chat_id == st.session_state.current_chat_id:
                label = f"📂 {label} (Atual)"
            
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(label, key=f"btn_{chat_id}"):
                    st.session_state.current_chat_id = chat_id
                    st.rerun()
            with c2:
                if st.button("x", key=f"del_{chat_id}", help="Apagar"):
                    delete_chat(chat_id)

        st.markdown("---")
        if st.button("Sair (Logout)"):
            st.session_state.logged_in = False
            st.rerun()

def main_app():
    # Configura API
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except:
        st.error("Erro na API Key.")
        st.stop()
    
    # Dados da sessão atual
    chat_id = st.session_state.current_chat_id
    current_chat = st.session_state.chats[chat_id]
    modo_atual = st.session_state.mode
    
    st.title("⚖️ Carmélio AI Suite")
    
    # --- ÁREA DE UPLOAD (Apenas no Modo Arquivo) ---
    if modo_atual == "Análise de Arquivos":
        if not current_chat["file"]:
            st.info("📂 Suporta: PDF (Docs), JPG/PNG (Prints/Fotos) e MP3/WAV (Áudios/Audiências)")
            uploaded_file = st.file_uploader("Carregar Arquivo", type=["pdf", "jpg", "png", "jpeg", "mp3", "wav", "m4a"], key=f"up_{chat_id}")
            
            if uploaded_file:
                with st.spinner("Processando arquivo multimodal..."):
                    # Salva com a extensão correta para o Google entender
                    ext = os.path.splitext(uploaded_file.name)[1]
                    if not ext: ext = ".tmp"
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    # Upload para o Google
                    file_ref = genai.upload_file(tmp_path)
                    
                    # Loop de espera (Crucial para vídeos/áudios grandes)
                    while file_ref.state.name == "PROCESSING":
                        time.sleep(1)
                        file_ref = genai.get_file(file_ref.name)
                    
                    # Salva metadados no chat
                    current_chat["file"] = file_ref
                    current_chat["file_type"] = ext.lower()
                    current_chat["title"] = f"Doc {datetime.now().strftime('%H:%M')}"
                    
                    # Mensagem Inicial Inteligente baseada no tipo
                    msg_inicial = "Arquivo analisado."
                    if ext in ['.mp3', '.wav', '.m4a']:
                        msg_inicial = "Áudio processado! Posso transcrever ou resumir o que foi falado."
                    elif ext in ['.jpg', '.png', '.jpeg']:
                        msg_inicial = "Imagem processada! Posso ler o texto (OCR) ou descrever a cena."
                    else:
                        msg_inicial = "Documento PDF lido com sucesso."
                        
                    current_chat["history"].append({"role": "assistant", "content": msg_inicial})
                    
                    os.remove(tmp_path)
                    st.rerun()
        else:
            st.success(f"Arquivo anexado: {current_chat['file'].display_name}")

    elif modo_atual == "Chat Jurídico (Livre)":
        st.caption("Modo Consultoria: Pergunte sobre leis, teses e prazos.")

    # --- EXIBIÇÃO DO CHAT ---
    for msg in current_chat["history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # --- PROCESSAMENTO DA PERGUNTA ---
    prompt = st.chat_input("Digite sua mensagem...")
    
    if prompt:
        # 1. Mostra msg do usuário
        with st.chat_message("user"):
            st.markdown(prompt)
        current_chat["history"].append({"role": "user", "content": prompt})
        
        # 2. Gera resposta
        with st.chat_message("assistant"):
            with st.spinner("Carmélio AI está pensando..."):
                try:
                    # Modelo Flash Latest (Melhor para multimídia)
                    model = genai.GenerativeModel("gemini-1.5-flash-latest")
                    
                    response_text = ""
                    
                    # Lógica Híbrida
                    if modo_atual == "Análise de Arquivos" and current_chat["file"]:
                        # Instrução Dinâmica
                        instruction = "Você é um Assistente Jurídico Especialista."
                        if current_chat["file_type"] in ['.mp3', '.wav', '.m4a']:
                            instruction += " O arquivo é um ÁUDIO. Se pedido, transcreva exatamente o que foi dito. Identifique falantes se possível."
                        elif current_chat["file_type"] in ['.jpg', '.png']:
                            instruction += " O arquivo é uma IMAGEM. Descreva visualmente e extraia todo texto legível (OCR)."
                        
                        # Monta histórico para API (incluindo o arquivo)
                        api_history = [
                            {"role": "user", "parts": [current_chat["file"], instruction]},
                            {"role": "model", "parts": ["Entendido. Arquivo carregado."]}
                        ]
                        # Adiciona contexto da conversa
                        for m in current_chat["history"]:
                            role = "model" if m["role"] == "assistant" else "user"
                            api_history.append({"role": role, "parts": [m["content"]]})
                        
                        # Remove a última msg do user pois ela vai no send_message
                        api_history.pop() 
                        
                        chat = model.start_chat(history=api_history)
                        response = chat.send_message(prompt)
                        response_text = response.text

                    elif modo_atual == "Chat Jurídico (Livre)":
                        # Chat puro sem arquivo
                        instruction = f"Atue como Advogado Sênior. Usuário: {st.session_state.username}. Responda com base na legislação brasileira."
                        chat = model.start_chat(history=[])
                        # Envia prompt com contexto de sistema
                        response = chat.send_message(f"Instrução do Sistema: {instruction}\n\nPergunta do Usuário: {prompt}")
                        response_text = response.text
                    
                    else:
                        response_text = "⚠️ Por favor, carregue um arquivo primeiro ou mude para o modo 'Chat Jurídico (Livre)' na barra lateral."

                    st.markdown(response_text)
                    current_chat["history"].append({"role": "assistant", "content": response_text})
                    
                except Exception as e:
                    st.error(f"Erro: {e}")

# --- 4. EXECUÇÃO ---
if not st.session_state.logged_in:
    login()
else:
    sidebar_menu()
    main_app()
