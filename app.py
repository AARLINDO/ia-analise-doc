import streamlit as st
import google.generativeai as genai

# ==============================================================================
# CONFIGURAÇÃO E CHAVE
# ==============================================================================
# COLE SUA CHAVE AQUI DENTRO DAS ASPAS
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
# CÉREBRO DA IA (COM SISTEMA ANTI-ERRO)
# ==============================================================================
def get_gemini_response(mode, user_input, file_data=None, mime_type=None):
    if "COLE_SUA" in CHAVE_MESTRA:
        return "⚠️ Erro: Você esqueceu de colocar a chave no código (linha 8)!"
        
    genai.configure(api_key=CHAVE_MESTRA)
    
    # Definição das Personas
    prompts = {
        "padrao": "Você é um assistente jurídico útil.",
        "oab": "ATUE COMO: Examinador OAB. Exija fundamentação legal (CLT/Súmulas).",
        "pcsc": "ATUE COMO: Mentor PCSC. Destaque pegadinhas da banca FGV/Cebraspe."
    }
    instruction = prompts.get(mode, "padrao")
    
    # Tenta usar o modelo 1.5 (Mais Inteligente)
    try:
        model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=instruction)
        content = [user_input]
        if file_data: content.append({"mime_type": mime_type, "data": file_data})
        return model.generate_content(content).text
    except Exception as e_flash:
        # Se der erro 404, tenta o modelo PRO (Mais Compatível)
        try:
            model = genai.GenerativeModel("gemini-pro") # Versão compatível antiga
            # O modelo antigo não aceita system_instruction direto, então injetamos no texto
            full_prompt = f"INSTRUÇÃO DO SISTEMA: {instruction}\n\nUSUÁRIO: {user_input}"
            content = [full_prompt]
            if file_data: 
                return "⚠️ O modelo antigo (Gemini Pro) não aceita arquivos. Tente apenas texto ou reinicie o app."
            return model.generate_content(content).text
        except Exception as e_pro:
            return f"Erro Fatal: {e_flash} | Tentativa Backup: {e_pro}"

# ==============================================================================
# INTERFACE
# ==============================================================================
st.title("✨ Carmélio AI: Gemini Power")

with st.sidebar:
    st.success("✅ Chave Conectada")
    modo_visual = st.radio("Modo:", ["🤖 Geral", "⚖️ Mentor OAB", "🚓 Mentor PCSC"])
    modo_map = {"🤖 Geral": "padrao", "⚖️ Mentor OAB": "oab", "🚓 Mentor PCSC": "pcsc"}
    
    if st.button("🗑️ Limpar Conversa"):
        st.session_state['chat_history'] = []
        st.rerun()

if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []

for msg in st.session_state['chat_history']:
    with st.chat_message(msg['role'], avatar="👤" if msg['role'] == "user" else "🤖"):
        st.markdown(msg['content'])

col1, col2 = st.columns([0.85, 0.15])
with col1: prompt = st.chat_input("Digite sua dúvida...")
with col2: uploaded_file = st.file_uploader("📎", type=["png", "jpg", "pdf"], label_visibility="collapsed")

if prompt:
    st.session_state['chat_history'].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"): st.markdown(prompt)
    
    file_bytes = None; mime = None
    if uploaded_file:
        file_bytes = uploaded_file.getvalue(); mime = uploaded_file.type
        st.info(f"Analisando arquivo: {uploaded_file.name}...")

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Pensando..."):
            resp = get_gemini_response(modo_map[modo_visual], prompt, file_bytes, mime)
            st.markdown(resp)
            st.session_state['chat_history'].append({"role": "assistant", "content": resp})
