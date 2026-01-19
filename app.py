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
    """Tela de Login Simples"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='text-align: center;'><h1>⚖️ Carmélio AI</h1><p>Acesso Restrito ao Sistema Jurídico</p></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        senha_digitada = st.text_input("Digite sua senha de acesso:", type="password")
        
        if st.button("Entrar no Sistema", type="primary"):
