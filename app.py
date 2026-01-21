import streamlit as st
import google.generativeai as genai
import os

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Studio", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background: linear-gradient(90deg, #4285F4, #9B72CB); color: white; border: none; font-weight: bold; }
    h1, h2, h3 { color: #E0E0E0; }
    .stSuccess { background-color: #1e3c25; color: #4caf50; border-radius: 5px; padding: 10px; }
    .stError { background-color: #3c1e1e; color: #ff5252; border-radius: 5px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# LÓGICA DE CONEXÃO (SEGURA)
# ==============================================================================
def get_gemini_response(prompt, context_text="", image_data=None, mime_type=None, mode="padrao"):
    # 1. Tenta pegar a chave do Cofre (Secrets)
    api_key = None
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        return "⚠️ ERRO DE CONFIGURAÇÃO: A chave não foi encontrada no 'Secrets'. Vá em Manage App > Settings > Secrets e configure a GOOGLE_API_KEY."

    # 2. Configura o Google
    genai.configure(api_key=api_key)
    
    # 3. Define as Personas
    personas = {
        "padrao": "Você é um assistente jurídico útil e preciso.",
        "oab": "ATUE COMO: Examinador da OAB (2ª Fase Trabalho). Exija fundamentação (Art. 840 CLT, Súmulas). Se for peça, exija valor da causa.",
        "pcsc": "ATUE COMO: Mentor PCSC (Escrivão). Foque em Inquérito Policial, Prisões e pegadinhas da banca FGV/Cebraspe."
    }
    
    # 4. Tenta modelos em ordem (Anti-Erro 404)
    models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    final_prompt = [prompt]
    if context_text: final_prompt.append(f"CONTEXTO DO ARQUIVO:\n{context_text}")
    if image_data: final_prompt.append({"mime_type": mime_type, "data": image_data})

    for model_name in models:
        try:
            # Modelo antigo não suporta imagem via lista direta as vezes, pulamos se tiver imagem
            if model_name == "gemini-pro" and image_data: continue
            
            instruction = personas[mode] if model_name != "gemini-pro" else None
            model = genai.GenerativeModel(model_name, system_instruction=instruction)
            
            # Adaptação para modelo antigo
            if model_name == "gemini-pro": final_prompt[0] = f"PERSONA: {personas[mode]}\n\n{prompt}"
            
            return model.generate_content(final_prompt).text
        except:
            continue # Tenta o próximo modelo se der erro
            
    return "❌ ERRO NO GOOGLE: Sua chave pode ter sido revogada ou expirou. Gere uma nova no Google AI Studio e atualize o Secrets."

# ==============================================================================
# INTERFACE DO USUÁRIO
# ==============================================================================
st.title("⚖️ Carmélio AI Studio")

# Verifica se a chave existe (Sem mostrar ela)
if "GOOGLE_API_KEY" in st.secrets:
    st.markdown('<div class="stSuccess">🔐 Sistema Conectado ao Cofre Seguro</div>', unsafe_allow_html=True)
    
    # --- BARRA LATERAL ---
    with st.sidebar:
        st.header("Configurações")
        mode = st.radio("Modo de Estudo:", ["🤖 Geral", "⚖️ OAB (Trabalho)", "🚓 PCSC (Escrivão)"])
        mode_map = {"🤖 Geral": "padrao", "⚖️ OAB (Trabalho)": "oab", "🚓 PCSC (Escrivão)": "pcsc"}
        
        st.divider()
        if st.button("🗑️ Limpar Conversa"):
            st.session_state['chat'] = []
            st.rerun()

    # --- ABAS PRINCIPAIS ---
    tab1, tab2 = st.tabs(["💬 Chat Mentor", "📄 Analisar Arquivo"])

    # ABA 1: CHAT
    with tab1:
        if 'chat' not in st.session_state: st.session_state['chat'] = []
        
        # Mostra histórico
        for msg in st.session_state['chat']:
            avatar = "👤" if msg['role'] == "user" else "⚖️"
            with st.chat_message(msg['role'], avatar=avatar):
                st.markdown(msg['content'])
        
        # Campo de pergunta
        if prompt := st.chat_input("Digite sua dúvida jurídica..."):
            st.session_state['chat'].append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            
            with st.chat_message("assistant", avatar="⚖️"):
                with st.spinner("Consultando jurisprudência e leis..."):
                    resp = get_gemini_response(prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})

    # ABA 2: ARQUIVOS
    with tab2:
        st.info("Faça upload de PDFs, Fotos de Processos ou Questões")
        uploaded = st.file_uploader("Arraste o arquivo aqui", type=["pdf", "jpg", "png", "jpeg"])
        
        if uploaded and st.button("Analisar Documento"):
            with st.spinner("O Gemini está lendo o arquivo..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response("Analise este documento detalhadamente. Se for questão, dê o gabarito. Se for peça, resuma.", image_data=bytes_data, mime_type=mime)
                st.markdown("### 📋 Análise do Documento")
                st.write(resp)

else:
    # Se não tiver chave no cofre, mostra aviso
    st.markdown('<div class="stError">⚠️ SISTEMA PARADO: Falta a Chave de API</div>', unsafe_allow_html=True)
    st.warning("""
    **Como resolver:**
    1. Vá no canto inferior direito desta tela > **Manage App**.
    2. Clique em **Settings** > **Secrets**.
    3. Cole sua chave nova assim: `GOOGLE_API_KEY = "AIzaSyA7OqKBYj8m_fufO1hulYqO-bWA-tKxJaI"`
    4. Salve e recarregue a página.
    """)
