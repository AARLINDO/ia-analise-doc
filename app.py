import streamlit as st
import google.generativeai as genai
import yt_dlp
import os

# ==============================================================================
# 1. CONFIGURAÇÃO VISUAL
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
# 2. SISTEMA DE CHAVE INTELIGENTE (COFRE OU MANUAL)
# ==============================================================================
def get_api_key():
    # Tenta pegar do Cofre (Secrets) para não precisar digitar
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except:
        # Se não tiver no cofre, pede na barra lateral (Fallback)
        return None

# ==============================================================================
# 3. CÉREBRO GEMINI (ANTI-ERRO 404)
# ==============================================================================
def get_gemini_response(api_key, prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    genai.configure(api_key=api_key)
    
    personas = {
        "padrao": "Você é um assistente jurídico útil.",
        "oab": "ATUE COMO: Examinador OAB. Exija fundamentação (Art. 840 CLT, Súmulas).",
        "pcsc": "ATUE COMO: Mentor PCSC. Foque em Processo Penal e pegadinhas da banca."
    }
    
    # Tenta modelos em ordem (Do mais novo para o mais antigo)
    models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    final_prompt = [prompt]
    if context_text: final_prompt.append(f"CONTEXTO:\n{context_text}")
    if image_data: final_prompt.append({"mime_type": mime_type, "data": image_data})

    for model_name in models:
        try:
            if model_name == "gemini-pro" and image_data: continue # Modelo antigo não lê imagem
            
            instruction = personas[mode] if model_name != "gemini-pro" else None
            model = genai.GenerativeModel(model_name, system_instruction=instruction)
            
            # Ajuste para modelo antigo que não aceita instrução no sistema
            if model_name == "gemini-pro":
                final_prompt[0] = f"PERSONA: {personas[mode]}\n\n{prompt}"
                
            return model.generate_content(final_prompt).text
        except:
            continue
            
    return "❌ Erro: Chave inválida ou API instável. Verifique se criou uma chave nova."

# ==============================================================================
# 4. INTERFACE
# ==============================================================================
st.title("⚖️ Carmélio AI Studio")

# Pega a chave
chave_secreta = get_api_key()

with st.sidebar:
    if chave_secreta:
        st.success("🔐 Chave Autenticada pelo Cofre")
        api_key = chave_secreta
    else:
        st.warning("⚠️ Chave não encontrada no Cofre")
        api_key = st.text_input("Cole sua chave aqui provisoriamente:", type="password")
    
    st.divider()
    mode = st.radio("Modo:", ["🤖 Geral", "⚖️ OAB", "🚓 PCSC"])
    mode_map = {"🤖 Geral": "padrao", "⚖️ OAB": "oab", "🚓 PCSC": "pcsc"}
    
    if st.button("🗑️ Limpar"):
        st.session_state['chat'] = []
        st.rerun()

# Só mostra o app se tiver chave
if api_key:
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
                    resp = get_gemini_response(api_key, prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})

    with tab2:
        uploaded = st.file_uploader("Upload", type=["pdf", "jpg", "png"])
        if uploaded and st.button("Analisar"):
            with st.spinner("Lendo..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response(api_key, "Descreva e analise este documento.", image_data=bytes_data, mime_type=mime)
                st.write(resp)
else:
    st.info("👈 Configure sua chave no menu 'Manage App > Settings > Secrets' para não precisar digitar sempre.")
