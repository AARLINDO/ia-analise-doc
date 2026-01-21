import streamlit as st
import google.generativeai as genai

# ==============================================================================
# CONFIGURAÇÃO VISUAL
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Studio 2.0", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background: linear-gradient(90deg, #4285F4, #9B72CB); color: white; border: none; font-weight: bold; }
    h1, h2, h3 { color: #E0E0E0; }
    .stSuccess, .stInfo, .stWarning { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# LÓGICA DO GEMINI 2.0
# ==============================================================================
def get_gemini_response(prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    # 1. PEGA A CHAVE DO COFRE
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ ERRO CRÍTICO: Chave não configurada no Secrets."

    # 2. DEFINE AS PERSONAS
    personas = {
        "padrao": "Você é um assistente jurídico de elite, atualizado com as leis brasileiras.",
        "oab": "ATUE COMO: Examinador da OAB (2ª Fase Trabalho). Seja rigoroso. Exija fundamentação (Art. 840 CLT, Súmulas).",
        "pcsc": "ATUE COMO: Mentor PCSC (Escrivão). Foque em Inquérito Policial, Prisões e pegadinhas da banca FGV/Cebraspe."
    }
    
    # 3. MODELO CORRETO (Encontrado no seu Scanner)
    # Usando o Gemini 2.0 Flash que apareceu na sua lista
    model_name = "gemini-2.0-flash"
    
    # Prepara o conteúdo
    content = [prompt]
    if context_text: content.append(f"CONTEXTO ADICIONAL:\n{context_text}")
    
    if image_data:
        content.append({"mime_type": mime_type, "data": image_data})

    try:
        # Configura o modelo
        model = genai.GenerativeModel(model_name, system_instruction=personas[mode])
        response = model.generate_content(content)
        return response.text

    except Exception as e:
        return f"❌ Erro ao conectar com Gemini 2.0: {str(e)}"

# ==============================================================================
# INTERFACE
# ==============================================================================
st.title("⚖️ Carmélio AI Studio 2.0")

# Verifica conexão visualmente
if "GOOGLE_API_KEY" in st.secrets:
    with st.sidebar:
        st.success(f"✅ Conectado: Gemini 2.0 Flash")
        st.divider()
        mode = st.radio("Modo de Estudo:", ["🤖 Geral", "⚖️ OAB", "🚓 PCSC"])
        mode_map = {"🤖 Geral": "padrao", "⚖️ OAB": "oab", "🚓 PCSC": "pcsc"}
        if st.button("🗑️ Limpar"):
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
                with st.spinner("Processando com Gemini 2.0..."):
                    resp = get_gemini_response(prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})

    # ARQUIVOS
    with tab2:
        uploaded = st.file_uploader("Upload (PDF/Img)", type=["pdf", "jpg", "png"])
        if uploaded and st.button("Analisar"):
            with st.spinner("Lendo documento..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response("Analise este documento detalhadamente.", image_data=bytes_data, mime_type=mime)
                st.write(resp)
else:
    st.error("🚫 Chave não encontrada no Secrets.")
