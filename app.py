import streamlit as st
import google.generativeai as genai

# ==============================================================================
# 1. CONFIGURAÇÃO VISUAL & ESTILO
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Super", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background: linear-gradient(90deg, #4285F4, #9B72CB); color: white; border: none; font-weight: bold; }
    h1, h2, h3 { color: #E0E0E0; }
    .stSuccess, .stInfo, .stWarning { border-radius: 8px; }
    /* Área de upload destacada */
    .stFileUploader { padding: 20px; border: 1px dashed #4285F4; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. INTELIGÊNCIA ARTIFICIAL (CÉREBRO)
# ==============================================================================
def get_gemini_response(prompt, file_data=None, mime_type=None, mode="padrao"):
    # --- CONEXÃO ---
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ ERRO: Configure a chave no Secrets."

    # --- PERSONAS INTELIGENTES ---
    personas = {
        "padrao": """
            Você é o Carmélio, um assistente jurídico de elite e especialista em cartórios.
            SUAS HABILIDADES:
            1. Se receber ÁUDIO: Transcreva fielmente tudo o que for falado. Indique quem fala se possível.
            2. Se receber IMAGEM DE DOCUMENTO: Faça a transcrição completa (Inteiro Teor). Se for manuscrito difícil, tente o seu melhor e marque [ilegível] onde não conseguir.
            3. Se receber PERGUNTA JURÍDICA: Responda com base na lei brasileira atualizada.
        """,
        "oab": "ATUE COMO: Examinador da OAB (2ª Fase Trabalho). Seja rigoroso. Exija fundamentação (Art. 840 CLT, Súmulas).",
        "pcsc": "ATUE COMO: Mentor PCSC (Escrivão). Foque em Inquérito Policial, Prisões e pegadinhas da banca FGV/Cebraspe."
    }
    
    # --- PREPARA O PACOTE PARA O GOOGLE ---
    # O modelo 'flash-latest' é excelente para áudio e visão e funciona na sua conta
    model_name = "gemini-flash-latest"
    
    content = []
    
    # Se tiver arquivo (Áudio ou Imagem), adiciona primeiro
    if file_data:
        content.append({"mime_type": mime_type, "data": file_data})
        
        # Se o usuário não escreveu nada, damos um empurrãozinho automático
        if not prompt:
            if "audio" in mime_type:
                prompt = "Transcreva este áudio detalhadamente."
            elif "image" in mime_type:
                prompt = "Transcreva o texto desta imagem (Inteiro Teor) ou analise o conteúdo."
    
    # Adiciona o texto do usuário
    if prompt:
        content.append(prompt)

    try:
        # Chama o modelo
        model = genai.GenerativeModel(model_name, system_instruction=personas[mode])
        response = model.generate_content(content)
        return response.text

    except Exception as e:
        return f"❌ Erro ao processar: {str(e)}"

# ==============================================================================
# 3. INTERFACE (CORPO)
# ==============================================================================
st.title("⚖️ Carmélio AI Super")

if "GOOGLE_API_KEY" in st.secrets:
    # --- BARRA LATERAL ---
    with st.sidebar:
        st.success("✅ Sistema Online")
        st.info("🎧 Ouvidos Ativos (Áudio)\n👁️ Visão Ativa (OCR/Fotos)")
        st.divider()
        
        mode = st.radio("Modo:", ["🤖 Geral/Cartório", "⚖️ OAB", "🚓 PCSC"])
        mode_map = {"🤖 Geral/Cartório": "padrao", "⚖️ OAB": "oab", "🚓 PCSC": "pcsc"}
        
        st.write("") # Espaço vazio
        if st.button("🗑️ Limpar Tudo"):
            st.session_state['chat'] = []
            st.rerun()

        # === ASSINATURA DO CRIADOR ===
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: #808080; margin-top: 20px;'>
                <small>Desenvolvido por</small><br>
                <b style='font-size: 16px; color: #E0E0E0;'>Arthur Carmélio</b>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # --- ABAS ---
    tab1, tab2 = st.tabs(["💬 Chat & Texto", "📂 Analisador de Arquivos (Foto/Áudio)"])

    # ABA 1: CHAT RÁPIDO
    with tab1:
        if 'chat' not in st.session_state: st.session_state['chat'] = []
        for msg in st.session_state['chat']:
            with st.chat_message(msg['role'], avatar="👤" if msg['role'] == "user" else "⚖️"):
                st.markdown(msg['content'])
        
        if prompt := st.chat_input("Digite sua dúvida, peça uma peça ou correção..."):
            st.session_state['chat'].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Carmélio pensando..."):
                    resp = get_gemini_response(prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})

    # ABA 2: UPLOAD (SUPER PODERES)
    with tab2:
        st.markdown("### 📤 Envie Documentos ou Áudios")
        st.caption("Suporta: Fotos de Livros, PDFs, Gravações de Voz, Audiências (MP3, WAV, JPG, PNG)")
        
        # Aceita ÁUDIO, IMAGEM e PDF
        uploaded = st.file_uploader("Arraste o arquivo aqui", type=["jpg", "png", "jpeg", "pdf", "mp3", "wav", "m4a", "ogg"])
        
        col1, col2 = st.columns([3, 1])
        with col1:
            user_instrucao = st.text_input("Instrução extra (Opcional):", placeholder="Ex: Transcreva em inteiro teor... ou Resuma este áudio...")
        with col2:
            st.write("") 
            st.write("") 
            processar = st.button("🚀 Processar Arquivo", use_container_width=True)

        if uploaded and processar:
            with st.spinner("⏳ Lendo, ouvindo e analisando..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                
                resp = get_gemini_response(user_instrucao, file_data=bytes_data, mime_type=mime, mode=mode_map[mode])
                
                st.divider()
                st.markdown("### 📋 Resultado:")
                st.write(resp)

else:
    st.error("🚫 Chave não encontrada no Secrets.")
