import streamlit as st
import google.generativeai as genai
import os

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Studio", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background: linear-gradient(90deg, #4285F4, #9B72CB); color: white; border: none; font-weight: bold; }
    h1, h2, h3 { color: #E0E0E0; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CONEXÃO AUTOMÁTICA (VIA SECRETS)
# ==============================================================================
def get_gemini_response(prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    # 1. Tenta pegar a chave do Secrets
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        return "⚠️ ERRO: O Secrets está vazio ou errado. Vá em Settings > Secrets e cole: GOOGLE_API_KEY = 'Sua_Chave'"

    genai.configure(api_key=api_key)
    
    personas = {
        "padrao": "Você é um assistente jurídico útil.",
        "oab": "ATUE COMO: Examinador OAB (Trabalho). Exija fundamentação (Art. 840 CLT).",
        "pcsc": "ATUE COMO: Mentor PCSC (Escrivão). Foque em Inquérito e pegadinhas."
    }
    
    # 2. Tenta modelos (Anti-Erro)
    models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    final_prompt = [prompt]
    if context_text: final_prompt.append(f"CONTEXTO:\n{context_text}")
    if image_data: final_prompt.append({"mime_type": mime_type, "data": image_data})

    for model_name in models:
        try:
            if model_name == "gemini-pro" and image_data: continue
            instruction = personas[mode] if model_name != "gemini-pro" else None
            model = genai.GenerativeModel(model_name, system_instruction=instruction)
            if model_name == "gemini-pro": final_prompt[0] = f"PERSONA: {personas[mode]}\n\n{prompt}"
            return model.generate_content(final_prompt).text
        except:
            continue
            
    return "❌ Erro: Chave inválida. Gere uma nova no Google AI Studio."

# ==============================================================================
# INTERFACE
# ==============================================================================
st.title("⚖️ Carmélio AI Studio")

# Verifica se a chave existe
if "GOOGLE_API_KEY" in st.secrets:
    st.success("🔐 Sistema Conectado")
    
    with st.sidebar:
        mode = st.radio("Modo:", ["🤖 Geral", "⚖️ OAB", "🚓 PCSC"])
        mode_map = {"🤖 Geral": "padrao", "⚖️ OAB": "oab", "🚓 PCSC": "pcsc"}
        if st.button("🗑️ Limpar"):
            st.session_state['chat'] = []
            st.rerun()

    tab1, tab2 = st.tabs(["💬 Chat", "📄 Arquivos"])

    with tab1:
        if 'chat' not in st.session_state: st.session_state['chat'] = []
        for msg in st.session_state['chat']:
            with st.chat_message(msg['role'], avatar="👤" if msg['role'] == "user" else "🤖"):
                st.markdown(msg['content'])
        
        if prompt := st.chat_input("Digite..."):
            st.session_state['chat'].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    resp = get_gemini_response(prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})

    with tab2:
        uploaded = st.file_uploader("Upload", type=["pdf", "jpg", "png"])
        if uploaded and st.button("Analisar"):
            with st.spinner("Lendo..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response("Analise este documento.", image_data=bytes_data, mime_type=mime)
                st.write(resp)
else:
    st.error("🚫 Falta configurar o Secrets (Passo 1)")
