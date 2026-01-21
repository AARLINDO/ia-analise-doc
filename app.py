import streamlit as st
import google.generativeai as genai

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Studio", page_icon="⚖️", layout="wide")

# Estilo para esconder menus padrões e deixar limpo
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background: linear-gradient(90deg, #4285F4, #9B72CB); color: white; border: none; font-weight: bold; }
    h1, h2, h3 { color: #E0E0E0; }
    .stSuccess, .stError, .stInfo { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CONEXÃO AUTOMÁTICA (INVISIBLE)
# ==============================================================================
def configure_gemini():
    # Tenta pegar a chave do cofre secreto do Streamlit
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except Exception:
        return False

def get_gemini_response(prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    personas = {
        "padrao": "Você é um assistente jurídico útil e preciso.",
        "oab": "ATUE COMO: Examinador da OAB (2ª Fase Trabalho). Exija fundamentação (Art. 840 CLT).",
        "pcsc": "ATUE COMO: Mentor PCSC (Escrivão). Foque em Inquérito e pegadinhas da banca."
    }
    
    # Sistema Anti-Erro (Tenta 3 modelos)
    models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    final_prompt = [prompt]
    if context_text: final_prompt.append(f"CONTEXTO DO ARQUIVO:\n{context_text}")
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
    return "❌ Erro de Conexão. Verifique sua chave no Secrets."

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================
st.title("⚖️ Carmélio AI Studio")

# Tenta conectar automaticamente
conectado = configure_gemini()

if conectado:
    # --- SISTEMA FUNCIONANDO (SEM PEDIR SENHA) ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2585/2585188.png", width=70)
        st.success("✅ Conectado")
        
        st.divider()
        st.header("🎓 Mentor")
        mode = st.radio("Modo de Estudo:", ["🤖 Geral", "⚖️ OAB (Trabalho)", "🚓 PCSC (Escrivão)"])
        mode_map = {"🤖 Geral": "padrao", "⚖️ OAB (Trabalho)": "oab", "🚓 PCSC (Escrivão)": "pcsc"}
        
        if st.button("🗑️ Limpar Conversa"):
            st.session_state['chat'] = []
            st.rerun()

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
                    resp = get_gemini_response(prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})

    # ARQUIVOS
    with tab2:
        uploaded = st.file_uploader("Upload de Documento", type=["pdf", "jpg", "png"])
        if uploaded and st.button("Analisar"):
            with st.spinner("Lendo..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response("Analise este documento.", image_data=bytes_data, mime_type=mime)
                st.markdown("### 📋 Análise")
                st.write(resp)

else:
    # --- TELA DE ERRO AMIGÁVEL (SE FALTAR A CHAVE NO COFRE) ---
    st.error("🚫 O sistema não encontrou a Chave de API.")
    st.info("""
    **Para funcionar sem pedir senha na tela, faça isso uma única vez:**
    
    1. Vá nas configurações deste site (canto inferior direito > **Manage App**).
    2. Clique nos três pontinhos (...) > **Settings**.
    3. Clique na aba **Secrets**.
    4. Cole exatamente isto lá dentro e Salve:
    """)
    st.code('GOOGLE_API_KEY = "AIzaSy_SUA_CHAVE_AQUI"', language="toml")
