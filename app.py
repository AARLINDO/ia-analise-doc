import streamlit as st
import google.generativeai as genai
import time
import os

# ==============================================================================
# 1. CONFIGURAÇÃO E CHAVE (FIXA)
# ==============================================================================
# COLE SUA CHAVE ABAIXO DENTRO DAS ASPAS
CHAVE_MESTRA = "AIzaSyDKSC9mAkeodr96m6SgcCvn70uZHseiM4A" 

st.set_page_config(page_title="Carmélio AI", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background: linear-gradient(45deg, #4285F4, #9B72CB); color: white; border: none; font-weight: bold; }
    h1, h2, h3 { color: #E0E0E0; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CÉREBRO DA IA
# ==============================================================================
def get_gemini_response(mode, user_input, file_data=None, mime_type=None):
    if "COLE_SUA" in CHAVE_MESTRA:
        return "⚠️ Erro: Você esqueceu de colocar a chave no código (linha 10 do app.py)!"
        
    genai.configure(api_key=CHAVE_MESTRA)
    
    system_prompts = {
        "padrao": "Você é um assistente jurídico útil.",
        "oab": "ATUE COMO: Examinador da OAB (2ª Fase Trabalho). Exija fundamentação (Art. CLT/Súmula) e valor da causa.",
        "pcsc": "ATUE COMO: Mentor PCSC (Escrivão). Destaque prazos de inquérito, pegadinhas da banca e crie uma questão no final."
    }
    
    # Tenta o modelo Flash (Rápido), se der erro tenta o Pro
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=system_prompts.get(mode, "padrao"))
        content = [user_input]
        if file_data: content.append({"mime_type": mime_type, "data": file_data})
        return model.generate_content(content).text
    except:
        # Fallback para versão Pro se o Flash falhar
        model = genai.GenerativeModel(model_name="gemini-1.5-pro", system_instruction=system_prompts.get(mode, "padrao"))
        content = [user_input]
        if file_data: content.append({"mime_type": mime_type, "data": file_data})
        return model.generate_content(content).text

# ==============================================================================
# 3. INTERFACE
# ==============================================================================
st.title("✨ Carmélio AI: Gemini Power")

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2585/2585188.png", width=60)
    st.success("✅ Chave Conectada Automaticamente")
    
    modo_visual = st.radio("Modo:", ["🤖 Geral", "⚖️ Mentor OAB", "🚓 Mentor PCSC"])
    modo_map = {"🤖 Geral": "padrao", "⚖️ Mentor OAB": "oab", "🚓 Mentor PCSC": "pcsc"}
    
    if st.button("🗑️ Limpar Conversa"):
        st.session_state['chat_history'] = []
        st.rerun()

# Chat
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []

for msg in st.session_state['chat_history']:
    with st.chat_message(msg['role'], avatar="👤" if msg['role'] == "user" else "🤖"):
        st.markdown(msg['content'])

# Inputs
col1, col2 = st.columns([0.85, 0.15])
with col1: prompt = st.chat_input("Digite sua dúvida...")
with col2: uploaded_file = st.file_uploader("📎", type=["png", "jpg", "pdf"], label_visibility="collapsed")

if prompt:
    st.session_state['chat_history'].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"): st.markdown(prompt)
    
    file_bytes = None
    mime = None
    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        mime = uploaded_file.type
        st.info(f"Analisando arquivo: {uploaded_file.name}...")

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Pensando..."):
            try:
                resp = get_gemini_response(modo_map[modo_visual], prompt, file_bytes, mime)
                st.markdown(resp)
                st.session_state['chat_history'].append({"role": "assistant", "content": resp})
            except Exception as e:
                st.error(f"Erro: {e}")
