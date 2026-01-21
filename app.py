import streamlit as st
import google.generativeai as genai

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
# BARRA LATERAL (ENTRADA MANUAL DA CHAVE)
# ==============================================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2585/2585188.png", width=60)
    st.header("🔐 Acesso Manual")
    
    # Campo para colar a chave (Obrigatório)
    api_key = st.text_input("Cole sua NOVA Google API Key:", type="password")
    
    if api_key:
        st.success("Chave Recebida!")
    else:
        st.warning("☝️ Cole a chave acima para começar.")

    st.divider()
    
    # Seletor de Modo
    mode = st.radio("Modo de Estudo:", ["🤖 Geral", "⚖️ OAB (Trabalho)", "🚓 PCSC (Escrivão)"])
    mode_map = {"🤖 Geral": "padrao", "⚖️ OAB (Trabalho)": "oab", "🚓 PCSC (Escrivão)": "pcsc"}
    
    if st.button("🗑️ Limpar Conversa"):
        st.session_state['chat'] = []
        st.rerun()

# ==============================================================================
# LÓGICA DO GEMINI
# ==============================================================================
def get_gemini_response(key, prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    # Configura com a chave que você colou na hora
    genai.configure(api_key=key)
    
    personas = {
        "padrao": "Você é um assistente jurídico útil e preciso.",
        "oab": "ATUE COMO: Examinador da OAB (2ª Fase Trabalho). Exija fundamentação (Art. 840 CLT).",
        "pcsc": "ATUE COMO: Mentor PCSC (Escrivão). Foque em Inquérito Policial e pegadinhas."
    }
    
    # Tenta conectar (Flash -> Pro -> Antigo)
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
            
    return "❌ Erro: Chave inválida. Verifique se copiou corretamente."

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================
st.title("⚖️ Carmélio AI Studio")

if api_key:
    tab1, tab2 = st.tabs(["💬 Chat Mentor", "📄 Analisar Arquivo"])

    # CHAT
    with tab1:
        if 'chat' not in st.session_state: st.session_state['chat'] = []
        for msg in st.session_state['chat']:
            with st.chat_message(msg['role'], avatar="👤" if msg['role'] == "user" else "⚖️"):
                st.markdown(msg['content'])
        
        if prompt := st.chat_input("Digite sua dúvida..."):
            st.session_state['chat'].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Analisando..."):
                    resp = get_gemini_response(api_key, prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})

    # ARQUIVOS
    with tab2:
        uploaded = st.file_uploader("Upload de Documento", type=["pdf", "jpg", "png"])
        if uploaded and st.button("Analisar"):
            with st.spinner("Lendo..."):
                bytes = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response(api_key, "Analise este documento.", image_data=bytes, mime_type=mime)
                st.write(resp)

else:
    st.info("👈 Cole sua Chave de API na barra lateral esquerda.")
