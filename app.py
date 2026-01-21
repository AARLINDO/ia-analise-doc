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
# LÓGICA ROBUSTA (TENTA TODOS OS MODELOS POSSÍVEIS)
# ==============================================================================
def get_gemini_response(prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    # 1. PEGA A CHAVE
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ ERRO: Chave não configurada no Secrets."

    # 2. LISTA DE MODELOS (Do melhor para o mais compatível)
    # Vamos tentar os nomes que apareceram no seu Scanner + os clássicos
    tentativas = [
        "gemini-flash-latest",   # Apareceu no seu scanner!
        "gemini-1.5-flash",      # Padrão
        "gemini-pro",            # Clássico (Funciona sempre)
        "gemini-1.5-pro-latest",
        "gemini-pro-vision"      # Antigo para imagens
    ]

    personas = {
        "padrao": "Você é um assistente jurídico de elite.",
        "oab": "ATUE COMO: Examinador OAB. Exija fundamentação (Art. 840 CLT).",
        "pcsc": "ATUE COMO: Mentor PCSC. Foque em Inquérito e pegadinhas."
    }
    
    # Prepara o conteúdo
    content = [prompt]
    if context_text: content.append(f"CONTEXTO:\n{context_text}")
    
    # Imagem só funciona em alguns modelos, vamos tratar isso
    if image_data:
        content.append({"mime_type": mime_type, "data": image_data})

    # 3. LOOP DE TENTATIVAS
    erros = []
    for modelo in tentativas:
        try:
            # Tenta configurar e gerar
            system_inst = personas[mode] if "vision" not in modelo and "gemini-pro" != modelo else None
            
            # Adaptação para modelos antigos que não aceitam system_instruction direto
            if system_inst is None: 
                final_content = [f"PERSONA: {personas[mode]}", *content]
            else:
                final_content = content

            model = genai.GenerativeModel(modelo, system_instruction=system_inst)
            response = model.generate_content(final_content)
            
            # Se chegou aqui, FUNCIONOU!
            return f"✅ (Respondido usando modelo: {modelo})\n\n{response.text}"
            
        except Exception as e:
            erros.append(f"{modelo}: {str(e)}")
            continue # Tenta o próximo da lista

    return f"❌ FALHA TOTAL: Nenhum modelo funcionou.\nErros: {erros}"

# ==============================================================================
# INTERFACE
# ==============================================================================
st.title("⚖️ Carmélio AI Studio")

if "GOOGLE_API_KEY" in st.secrets:
    with st.sidebar:
        st.success("✅ Sistema Conectado")
        st.info("Usando Seletor Automático de Modelos")
        st.divider()
        mode = st.radio("Modo:", ["🤖 Geral", "⚖️ OAB", "🚓 PCSC"])
        mode_map = {"🤖 Geral": "padrao", "⚖️ OAB": "oab", "🚓 PCSC": "pcsc"}
        if st.button("🗑️ Limpar"):
            st.session_state['chat'] = []
            st.rerun()

    tab1, tab2 = st.tabs(["💬 Chat", "📄 Arquivos"])

    with tab1:
        if 'chat' not in st.session_state: st.session_state['chat'] = []
        for msg in st.session_state['chat']:
            with st.chat_message(msg['role'], avatar="👤" if msg['role'] == "user" else "⚖️"):
                st.markdown(msg['content'])
        
        if prompt := st.chat_input("Digite sua dúvida..."):
            st.session_state['chat'].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Testando modelos disponíveis..."):
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
    st.error("🚫 Chave não encontrada no Secrets.")
