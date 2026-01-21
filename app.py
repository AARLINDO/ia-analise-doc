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
# LÓGICA DO GEMINI (COM MODO COMPATIBILIDADE)
# ==============================================================================
def get_gemini_response(prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    # 1. PEGA A CHAVE DO COFRE
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ ERRO: Chave não configurada no Secrets."

    # 2. DEFINE AS PERSONAS
    personas = {
        "padrao": "Você é um assistente jurídico útil e direto.",
        "oab": "ATUE COMO: Examinador OAB. Exija fundamentação (Art. 840 CLT, Súmulas).",
        "pcsc": "ATUE COMO: Mentor PCSC. Foque em Inquérito e pegadinhas da banca."
    }
    
    # 3. LISTA DE TENTATIVAS (Do mais moderno para o mais compatível)
    # Tenta o 1.5 Flash primeiro. Se falhar, tenta o Pro 1.0 (que funciona sempre)
    models_to_try = ["gemini-1.5-flash", "gemini-pro"]
    
    # Prepara o conteúdo
    content = [prompt]
    if context_text: content.append(f"CONTEXTO:\n{context_text}")
    
    # Se tiver imagem, só o modelo novo aceita bem. O antigo precisa de tratamento.
    if image_data:
        content.append({"mime_type": mime_type, "data": image_data})

    last_error = ""

    for model_name in models_to_try:
        try:
            # Configurações específicas para cada versão
            if model_name == "gemini-pro":
                # O modelo antigo (Pro) não aceita imagens desse jeito
                if image_data: 
                    return "⚠️ O 'Modo Compatibilidade' foi ativado e ele não aceita imagens/PDFs, apenas texto. Tente copiar e colar o texto do documento."
                
                # O modelo antigo não aceita instrução de sistema direto, então injetamos no texto
                full_prompt = f"INSTRUÇÃO DO SISTEMA: {personas[mode]}\n\nUSUÁRIO: {prompt}"
                model = genai.GenerativeModel("gemini-pro")
                response = model.generate_content(full_prompt)
                return response.text
            
            else:
                # Modelos Novos (1.5 Flash)
                model = genai.GenerativeModel(model_name, system_instruction=personas[mode])
                response = model.generate_content(content)
                return response.text

        except Exception as e:
            last_error = str(e)
            continue # Se der erro, pula para o próximo modelo da lista (gemini-pro)

    return f"❌ Erro Fatal: O sistema tentou todos os modelos e falhou. Detalhe: {last_error}"

# ==============================================================================
# INTERFACE
# ==============================================================================
st.title("⚖️ Carmélio AI Studio")

# Verifica conexão visualmente
if "GOOGLE_API_KEY" in st.secrets:
    with st.sidebar:
        st.success("✅ Conectado (Seguro)")
        st.divider()
        mode = st.radio("Modo:", ["🤖 Geral", "⚖️ OAB", "🚓 PCSC"])
        mode_map = {"🤖 Geral": "padrao", "⚖️ OAB": "oab", "🚓 PCSC": "pcsc"}
        if st.button("🗑️ Limpar"):
            st.session_state['chat'] = []
            st.rerun()

    tab1, tab2 = st.tabs(["💬 Chat", "📄 Arquivos"])

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
                with st.spinner("Processando..."):
                    resp = get_gemini_response(prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})

    # ARQUIVOS
    with tab2:
        uploaded = st.file_uploader("Upload (PDF/Img)", type=["pdf", "jpg", "png"])
        if uploaded and st.button("Analisar"):
            with st.spinner("Lendo..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response("Analise este documento.", image_data=bytes_data, mime_type=mime)
                st.write(resp)
else:
    st.error("🚫 Chave não encontrada no Secrets.")
