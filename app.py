import streamlit as st
import google.generativeai as genai

# ==============================================================================
# CONFIGURAÇÃO VISUAL
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Studio", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background: linear-gradient(90deg, #4285F4, #9B72CB); color: white; border: none; font-weight: bold; }
    h1, h2, h3 { color: #E0E0E0; }
    .stSuccess, .stInfo, .stWarning { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# LÓGICA DEFINITIVA (USANDO O MODELO DESCOBERTO)
# ==============================================================================
def get_gemini_response(prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ ERRO: Chave não configurada no Secrets."

    # PERSONAS
    personas = {
        "padrao": "Você é um assistente jurídico de elite, especialista em leis brasileiras.",
        "oab": "ATUE COMO: Examinador da OAB (2ª Fase Trabalho). Seja rigoroso. Exija fundamentação (Art. 840 CLT, Súmulas).",
        "pcsc": "ATUE COMO: Mentor PCSC (Escrivão). Foque em Inquérito Policial, Prisões e pegadinhas da banca FGV/Cebraspe."
    }
    
    # O MODELO VENCEDOR (Descoberto no seu teste)
    # Este modelo é rápido, grátis e compatível com sua conta
    model_name = "gemini-flash-latest"
    
    # Prepara o conteúdo
    content = [prompt]
    if context_text: content.append(f"CONTEXTO ADICIONAL:\n{context_text}")
    
    if image_data:
        content.append({"mime_type": mime_type, "data": image_data})

    try:
        model = genai.GenerativeModel(model_name, system_instruction=personas[mode])
        response = model.generate_content(content)
        return response.text

    except Exception as e:
        # Se der algum soluço, o plano B é o modelo clássico
        try:
            model_backup = genai.GenerativeModel("gemini-pro")
            return model_backup.generate_content(f"PERSONA: {personas[mode]}\n\n{prompt}").text
        except:
            return f"❌ Erro de Conexão: {str(e)}"

# ==============================================================================
# INTERFACE
# ==============================================================================
st.title("⚖️ Carmélio AI Studio")

if "GOOGLE_API_KEY" in st.secrets:
    with st.sidebar:
        st.success("✅ Conectado e Pronto")
        st.divider()
        mode = st.radio("Modo de Estudo:", ["🤖 Geral", "⚖️ OAB", "🚓 PCSC"])
        mode_map = {"🤖 Geral": "padrao", "⚖️ OAB": "oab", "🚓 PCSC": "pcsc"}
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
        uploaded = st.file_uploader("Upload (PDF/Img)", type=["pdf", "jpg", "png"])
        if uploaded and st.button("Analisar"):
            with st.spinner("Lendo documento..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response("Analise este documento detalhadamente.", image_data=bytes_data, mime_type=mime)
                st.write(resp)
else:
    st.error("🚫 Chave não encontrada no Secrets.")
