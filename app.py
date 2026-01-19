import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
from datetime import datetime

# --- 1. CONFIGURAÇÃO INICIAL E CSS ---
st.set_page_config(
    page_title="Carmélio AI - Workspace",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS para deixar com cara de App Profissional (Gemini Style)
st.markdown("""
<style>
    /* Esconder elementos padrões do Streamlit */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    
    /* Estilo da Tela de Login */
    .login-container {
        margin-top: 100px;
        padding: 40px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    /* Botões da Sidebar (Parecidos com o Gemini) */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        text-align: left;
        padding-left: 15px;
    }
    
    /* Área de Chat */
    .chat-container {
        max-width: 800px;
        margin: auto;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. GERENCIAMENTO DE ESTADO (MEMÓRIA) ---
# Inicializa as variáveis se não existirem
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "chats" not in st.session_state:
    # Cria o primeiro chat vazio
    st.session_state.chats = {
        "chat_1": {"title": "Nova Conversa", "history": [], "file": None}
    }
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = "chat_1"

# --- 3. FUNÇÕES DO SISTEMA ---
def login():
    """Tela de Login Multi-Usuário"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='text-align: center;'><h1>⚖️ Carmélio AI</h1><p>Acesso Restrito ao Sistema Jurídico</p></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Agora pedimos Usuário E Senha
        usuario = st.text_input("Usuário:")
        senha_digitada = st.text_input("Senha:", type="password")
        
        if st.button("Entrar no Sistema", type="primary"):
            # Busca a lista de senhas nos segredos
            usuarios_cadastrados = st.secrets.get("passwords", {})
            
            # Verifica se o usuário existe E se a senha bate
            if usuario in usuarios_cadastrados and usuarios_cadastrados[usuario] == senha_digitada:
                st.session_state.logged_in = True
                st.session_state.username = usuario # Salva quem entrou
                st.toast(f"Bem-vindo, {usuario}!", icon="🔓")
                time.sleep(1)
                st.rerun()
            else:
                st.error("🔒 Usuário ou senha incorretos.")

def create_new_chat():
    """Cria uma nova aba de conversa"""
    new_id = f"chat_{len(st.session_state.chats) + 1}"
    st.session_state.chats[new_id] = {
        "title": f"Conversa {len(st.session_state.chats) + 1}", 
        "history": [], 
        "file": None
    }
    st.session_state.current_chat_id = new_id
    st.rerun()

def delete_chat(chat_id):
    """Apaga uma conversa"""
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[chat_id]
        # Muda para o primeiro chat disponível
        st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
        st.rerun()

def sidebar_menu():
    """Barra lateral estilo Gemini"""
    with st.sidebar:
        st.markdown("### 🗂️ Histórico")
        
        # Botão Nova Conversa
        if st.button("➕ Nova Conversa", type="primary"):
            create_new_chat()
        
        st.markdown("---")
        
        # Lista de Conversas (Itera sobre o dicionário de chats)
        # Convertemos para lista para poder reverter (mais recentes no topo se quiséssemos)
        for chat_id, chat_data in st.session_state.chats.items():
            # Define se o botão parece "ativo" ou não
            label = chat_data["title"]
            if chat_id == st.session_state.current_chat_id:
                label = f"📂 {label} (Atual)"
            
            col_a, col_b = st.columns([4, 1])
            with col_a:
                if st.button(label, key=f"btn_{chat_id}"):
                    st.session_state.current_chat_id = chat_id
                    st.rerun()
            with col_b:
                if st.button("❌", key=f"del_{chat_id}", help="Apagar"):
                    delete_chat(chat_id)

        st.markdown("---")
        
        # Área do Usuário
        with st.expander(f"👤 {st.session_state.get('username', 'Usuário')}"):
            st.caption("Conectado")
            if st.button("Sair (Logout)"):
                st.session_state.logged_in = False
                st.rerun()

def main_app():
    """A Aplicação Principal"""
    
    # 1. Configurar API
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        st.error("Erro na API Key. Verifique os Secrets.")
        st.stop()
    
    # Pega dados do chat atual
    chat_id = st.session_state.current_chat_id
    current_chat = st.session_state.chats[chat_id]
    
    # --- CABEÇALHO DO CHAT ---
    st.markdown(f"### {current_chat['title']}")
    
    # --- ÁREA DE UPLOAD (DENTRO DO CHAT) ---
    if not current_chat["file"]:
        st.info("Para começar, anexe um documento a esta conversa.")
        uploaded_file = st.file_uploader("Upload PDF/Imagem", type=["pdf", "jpg", "png"], key=f"uploader_{chat_id}")
        
        if uploaded_file:
            with st.spinner("Processando arquivo..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                # Upload para o Google
                file_ref = genai.upload_file(tmp_path)
                while file_ref.state.name == "PROCESSING":
                    time.sleep(2)
                    file_ref = genai.get_file(file_ref.name)
                
                # Salva no estado do chat atual
                st.session_state.chats[chat_id]["file"] = file_ref
                # Define título automático baseado na hora
                st.session_state.chats[chat_id]["title"] = f"Doc {datetime.now().strftime('%H:%M')}"
                # Mensagem inicial
                st.session_state.chats[chat_id]["history"].append(
                    {"role": "assistant", "content": "Documento analisado! O que você deseja saber?"}
                )
                os.remove(tmp_path)
                st.rerun()
    
    else:
        # Se já tem arquivo, mostra um aviso discreto
        st.success(f"📎 Documento anexado. (ID: {chat_id})")
    
    # --- EXIBIR MENSAGENS ---
    for msg in current_chat["history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # --- CAMPO DE INPUT ---
    prompt = st.chat_input("Digite sua mensagem...")
    
    if prompt:
        # 1. Adiciona pergunta do usuário
        with st.chat_message("user"):
            st.markdown(prompt)
        current_chat["history"].append({"role": "user", "content": prompt})
        
        # 2. Resposta da IA
        if current_chat["file"]:
            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    try:
                        model = genai.GenerativeModel("gemini-1.5-flash-latest", 
                            system_instruction="Você é um assistente jurídico sênior. Responda de forma formal e direta.")
                        
                        # Monta histórico para API
                        api_history = [
                            {"role": "user", "parts": [current_chat["file"], "Analise este arquivo."]},
                            {"role": "model", "parts": ["Entendido."]}
                        ]
                        
                        # Adiciona mensagens anteriores para contexto
                        for old_msg in current_chat["history"]:
                            if old_msg["role"] == "user":
                                api_history.append({"role": "user", "parts": [old_msg["content"]]})
                            else:
                                api_history.append({"role": "model", "parts": [old_msg["content"]]})
                        
                        # Remove a última mensagem do user do histórico (pois ela vai no send_message)
                        api_history.pop() 
                        
                        chat_session = model.start_chat(history=api_history)
                        response = chat_session.send_message(prompt)
                        
                        st.markdown(response.text)
                        current_chat["history"].append({"role": "assistant", "content": response.text})
                        
                    except Exception as e:
                        st.error(f"Erro: {e}")
        else:
            st.warning("⚠️ Por favor, faça upload de um documento primeiro.")

# --- 4. CONTROLE DE FLUXO PRINCIPAL ---
if not st.session_state.logged_in:
    login()
else:
    sidebar_menu()
    main_app()

