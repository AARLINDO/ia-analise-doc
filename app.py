import streamlit as st
import google.generativeai as genai

# ==============================================================================
# 1. CONFIGURAÇÃO VISUAL
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Studio", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background: linear-gradient(90deg, #4285F4, #9B72CB); color: white; border: none; font-weight: bold; }
    h1, h2, h3 { color: #E0E0E0; }
    .stSuccess { background-color: #1e3c25; color: #4caf50; padding: 10px; border-radius: 5px; }
    .stWarning { background-color: #3c3c1e; color: #ffff00; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. BARRA LATERAL (AQUI É O LUGAR PARA COLOCAR A CHAVE)
# ==============================================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2585/2585188.png", width=70)
    st.header("🔐 Acesso Seguro")
    
    # --- CAMPO PARA COLAR A CHAVE NA TELA ---
    api_key_input = st.text_input("Cole sua Google API Key aqui:", type="password", help="A chave começa com AIza...")
    
    # Verifica se a chave foi colada
    if api_key_input:
        if api_key_input.startswith("AIza"):
            st.success("✅ Chave Válida!")
        else:
            st.error("❌ A chave parece errada (deve começar com AIza)")
    else:
        st.warning("👈 Cole a chave para liberar o sistema.")

    st.divider()
    
    # SELETOR DE MENTOR
    st.subheader("🎓 Escolha o Mentor")
    mode = st.radio("Modo de Estudo:", ["🤖 Geral", "⚖️ OAB (Trabalho)", "🚓 PCSC (Escrivão)"])
    mode_map = {"🤖 Geral": "padrao", "⚖️ OAB (Trabalho)": "oab", "🚓 PCSC (Escrivão)": "pcsc"}
    
    if st.button("🗑️ Limpar Conversa"):
        st.session_state['chat'] = []
        st.rerun()

# ==============================================================================
# 3. LÓGICA DO GEMINI (INTELIGÊNCIA)
# ==============================================================================
def get_gemini_response(key, prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    # Configura o Google com a chave da tela
    genai.configure(api_key=key)
    
    personas = {
        "padrao": "Você é um assistente jurídico útil e preciso.",
        "oab": "ATUE COMO: Examinador da OAB (2ª Fase Trabalho). Exija fundamentação (Art. 840 CLT, Súmulas). Se for peça, exija valor da causa.",
        "pcsc": "ATUE COMO: Mentor PCSC (Escrivão). Foque em Inquérito Policial, Prisões e pegadinhas da banca FGV/Cebraspe."
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
            
    return "❌ Erro: A chave inserida não funcionou. Gere uma nova no Google AI Studio."

# ==============================================================================
# 4. TELA PRINCIPAL
# ==============================================================================
st.title("⚖️ Carmélio AI Studio")

if api_key_input and api_key_input.startswith("AIza"):
    # SE TEM CHAVE, MOSTRA O APP
    tab1, tab2 = st.tabs(["💬 Chat Mentor", "📄 Analisar Arquivo"])

    # ABA CHAT
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
                    resp = get_gemini_response(api_key_input, prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})

    # ABA ARQUIVOS
    with tab2:
        uploaded = st.file_uploader("Upload de Documento (PDF/Foto)", type=["pdf", "jpg", "png"])
        if uploaded and st.button("Analisar Documento"):
            with st.spinner("Lendo..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response(api_key_input, "Analise este documento.", image_data=bytes_data, mime_type=mime)
                st.markdown("### 📋 Análise")
                st.write(resp)

else:
    # SE NÃO TEM CHAVE, MOSTRA AVISO
    st.info("👈 **PASSO 1:** Cole sua Chave de API na barra lateral esquerda.")
    st.warning("Se você não tem uma chave, crie uma grátis em: https://aistudio.google.com/app/apikey")
