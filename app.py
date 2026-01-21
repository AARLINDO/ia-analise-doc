import streamlit as st
import google.generativeai as genai
import time
import os

# ==============================================================================
# 1. CONFIGURAÇÃO VISUAL
# ==============================================================================
st.set_page_config(
    page_title="Carmélio AI - Gemini Edition",
    page_icon="⚖️",
    layout="wide"
)

# Estilo visual moderno
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button {
        background: linear-gradient(45deg, #4285F4, #9B72CB);
        color: white; border: none; font-weight: bold;
    }
    h1, h2, h3 { color: #E0E0E0; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CÉREBRO DA IA (GOOGLE GEMINI)
# ==============================================================================
def get_gemini_response(api_key, mode, user_input, file_data=None, mime_type=None):
    # Configura a chave
    genai.configure(api_key=api_key)
    
    # Define as personalidades (Personas)
    system_prompts = {
        "padrao": "Você é um assistente jurídico útil e direto.",
        "oab": """
            ATUE COMO: Examinador rigoroso da OAB (2ª Fase Trabalho).
            SUA MISSÃO: Garantir que o aluno passe na prova.
            REGRAS:
            1. Sempre cite o Artigo da CLT ou Súmula do TST.
            2. Se for uma Peça, exija qualificação completa e VALOR DA CAUSA (Art. 840 CLT).
            3. Corrija termos errados (ex: não use 'Autor', use 'Reclamante').
        """,
        "pcsc": """
            ATUE COMO: Professor Especialista em Carreiras Policiais (Foco: PCSC Escrivão).
            SUA MISSÃO: Ensinar o conteúdo focado na banca (FGV/Cebraspe).
            REGRAS:
            1. Destaque "pegadinhas" comuns sobre Inquérito Policial e Prisão.
            2. Use mnemônicos para ajudar a decorar.
            3. No final de cada explicação, crie uma QUESTÃO DE PROVA inédita sobre o tema.
        """
    }
    
    # Escolhe o modelo (Flash é rápido, Pro é inteligente)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", 
        system_instruction=system_prompts.get(mode, "padrao")
    )
    
    # Monta o conteúdo para enviar
    content = [user_input]
    
    # Se tiver arquivo (imagem ou pdf), adiciona ao pacote
    if file_data:
        image_part = {"mime_type": mime_type, "data": file_data}
        content.append(image_part)
        
    # Gera a resposta
    response = model.generate_content(content)
    return response.text

# ==============================================================================
# 3. INTERFACE (O QUE VOCÊ VÊ)
# ==============================================================================
st.title("✨ Carmélio AI: Gemini Power")

# --- BARRA LATERAL (Configurações) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2585/2585188.png", width=60)
    st.markdown("### ⚙️ Configuração")
    
    # Tenta pegar a chave dos segredos, senão pede na tela
    api_key = st.secrets.get("GOOGLE_API_KEY", None)
    if not api_key:
        api_key = st.text_input("Cole sua Google API Key aqui:", type="password")
        st.caption("[Pegue sua chave aqui](https://aistudio.google.com/app/apikey)")
    
    st.divider()
    
    # Seletor de Modo
    modo_visual = st.radio("Escolha o Modo:", ["🤖 Geral", "⚖️ Mentor OAB", "🚓 Mentor PCSC"])
    modo_map = {"🤖 Geral": "padrao", "⚖️ Mentor OAB": "oab", "🚓 Mentor PCSC": "pcsc"}
    modo_selecionado = modo_map[modo_visual]
    
    if st.button("🗑️ Limpar Conversa"):
        st.session_state['chat_history'] = []
        st.rerun()

# --- ÁREA DE CHAT ---
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# Mostra mensagens antigas
for msg in st.session_state['chat_history']:
    icon = "👤" if msg['role'] == "user" else "🤖"
    with st.chat_message(msg['role'], avatar=icon):
        st.markdown(msg['content'])

# --- ENTRADA DE DADOS (Texto e Arquivo) ---
col1, col2 = st.columns([0.85, 0.15])
with col1:
    prompt = st.chat_input("Digite sua dúvida ou peça um simulado...")
with col2:
    uploaded_file = st.file_uploader("📎", type=["png", "jpg", "jpeg", "pdf"], label_visibility="collapsed")

# Processamento
if prompt and api_key:
    # Mostra mensagem do usuário
    st.session_state['chat_history'].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    # Prepara arquivo se houver
    file_bytes = None
    mime = None
    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        mime = uploaded_file.type
        st.info(f"Analisando arquivo: {uploaded_file.name}...")

    # Resposta da IA
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Consultando base de dados..."):
            try:
                resposta = get_gemini_response(api_key, modo_selecionado, prompt, file_bytes, mime)
                st.markdown(resposta)
                st.session_state['chat_history'].append({"role": "assistant", "content": resposta})
            except Exception as e:
                st.error(f"Erro: {e}")
                
elif prompt and not api_key:
    st.warning("⚠️ Você precisa colocar a Chave de API na barra lateral primeiro!")
