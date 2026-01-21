import streamlit as st
import google.generativeai as genai
import yt_dlp
import os

# ==============================================================================
# 1. CONFIGURAÇÃO VISUAL
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Studio", page_icon="⚖️", layout="wide")

# 👇👇👇 LINHA 12: COLE SUA CHAVE NOVA AQUI DENTRO DAS ASPAS 👇👇👇
CHAVE_FIXA = "AIzaSyCwu8EgBD7Xu3gcZHrwILA_2nyUW1ic0us"

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background: linear-gradient(90deg, #4285F4, #9B72CB); color: white; border: none; font-weight: bold; }
    h1, h2, h3 { color: #E0E0E0; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. INTELIGÊNCIA (GEMINI)
# ==============================================================================
def get_gemini_response(prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    # Verifica se a chave foi colada
    if "COLE_SUA" in CHAVE_FIXA:
        return "⚠️ ERRO: Você esqueceu de colar a chave na Linha 12 do código!"
        
    genai.configure(api_key=CHAVE_FIXA)
    
    personas = {
        "padrao": "Você é um assistente jurídico útil.",
        "oab": "ATUE COMO: Examinador OAB (Trabalho). Exija fundamentação (Art. 840 CLT).",
        "pcsc": "ATUE COMO: Mentor PCSC (Escrivão). Foque em Inquérito e pegadinhas."
    }
    
    # Tenta conectar em ordem de inteligência
    models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    final_prompt = [prompt]
    if context_text: final_prompt.append(f"CONTEXTO:\n{context_text}")
    if image_data: final_prompt.append({"mime_type": mime_type, "data": image_data})

    for model_name in models:
        try:
            if model_name == "gemini-pro" and image_data: continue
            instruction = personas[mode] if model_name != "gemini-pro" else None
            model = genai.GenerativeModel(model_name, system_instruction=instruction)
            
            # Compatibilidade com modelo antigo
            if model_name == "gemini-pro": final_prompt[0] = f"PERSONA: {personas[mode]}\n\n{prompt}"
                
            return model.generate_content(final_prompt).text
        except:
            continue
            
    return "❌ Erro: Chave inválida ou bloqueada pelo Google. Gere uma nova."

# ==============================================================================
# 3. INTERFACE
# ==============================================================================
st.title("⚖️ Carmélio AI Studio")

with st.sidebar:
    if "AIza" in CHAVE_FIXA:
        st.success("🔐 Chave Conectada (Linha 12)")
    else:
        st.error("⚠️ Sem Chave (Edite a Linha 12)")
        
    mode = st.radio("Modo:", ["🤖 Geral", "⚖️ OAB", "🚓 PCSC"])
    mode_map = {"🤖 Geral": "padrao", "⚖️ OAB": "oab", "🚓 PCSC": "pcsc"}
    
    if st.button("🗑️ Limpar"):
        st.session_state['chat'] = []
        st.rerun()

# Abas
tab1, tab2 = st.tabs(["💬 Chat", "📄 Arquivos"])

# Chat
with tab1:
    if 'chat' not in st.session_state: st.session_state['chat'] = []
    for msg in st.session_state['chat']:
        with st.chat_message(msg['role'], avatar="👤" if msg['role'] == "user" else "🤖"):
            st.markdown(msg['content'])
            
    if prompt := st.chat_input("Digite sua dúvida..."):
        st.session_state['chat'].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                resp = get_gemini_response(prompt, mode=mode_map[mode])
                st.markdown(resp)
                st.session_state['chat'].append({"role": "assistant", "content": resp})

# Arquivos
with tab2:
    uploaded = st.file_uploader("Upload PDF/Foto", type=["pdf", "jpg", "png"])
    if uploaded and st.button("Analisar"):
        with st.spinner("Lendo..."):
            bytes_data = uploaded.getvalue()
            mime = uploaded.type
            resp = get_gemini_response("Analise este documento.", image_data=bytes_data, mime_type=mime)
            st.write(resp)
