import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO

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
    .stFileUploader { padding: 20px; border: 1px dashed #4285F4; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÃO AUXILIAR: CRIAR WORD
# ==============================================================================
def criar_docx(texto):
    doc = Document()
    doc.add_heading('Resposta Carmélio AI', 0)
    doc.add_paragraph(texto)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==============================================================================
# 2. INTELIGÊNCIA ARTIFICIAL
# ==============================================================================
def get_gemini_response(prompt, file_data=None, mime_type=None, mode="padrao"):
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ ERRO: Configure a chave no Secrets."

    personas = {
        "padrao": """
            Você é o Carmélio, um assistente jurídico de elite e especialista em cartórios.
            SUAS HABILIDADES:
            1. ÁUDIO/IMAGEM: Transcreva fielmente (Inteiro Teor). Use formatação formal de cartório.
            2. PERGUNTAS: Responda com base na lei, citando artigos quando necessário.
            3. FORMATAÇÃO: Use tópicos e parágrafos claros para facilitar a leitura.
        """,
        "oab": "ATUE COMO: Examinador da OAB. Corrija peças, aponte erros e exija fundamentação (Art. 840 CLT).",
        "pcsc": "ATUE COMO: Mentor PCSC. Foque em Inquérito Policial, Prisões e pegadinhas da banca."
    }
    
    model_name = "gemini-flash-latest"
    
    content = []
    if file_data:
        content.append({"mime_type": mime_type, "data": file_data})
        if not prompt:
            if "audio" in mime_type: prompt = "Transcreva este áudio em formato de termo formal."
            elif "image" in mime_type: prompt = "Transcreva o texto desta imagem (Inteiro Teor)."
    
    if prompt: content.append(prompt)

    try:
        model = genai.GenerativeModel(model_name, system_instruction=personas[mode])
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"❌ Erro ao processar: {str(e)}"

# ==============================================================================
# 3. INTERFACE
# ==============================================================================
st.title("⚖️ Carmélio AI Super")

if "GOOGLE_API_KEY" in st.secrets:
    with st.sidebar:
        st.success("✅ Sistema Online")
        st.info("🎧 Ouvidos Ativos\n👁️ Visão Ativa\n📄 Exportação Word")
        st.divider()
        
        mode = st.radio("Modo:", ["🤖 Geral/Cartório", "⚖️ OAB", "🚓 PCSC"])
        mode_map = {"🤖 Geral/Cartório": "padrao", "⚖️ OAB": "oab", "🚓 PCSC": "pcsc"}
        
        if st.button("🗑️ Limpar Tudo"):
            st.session_state['chat'] = []
            st.rerun()

        st.markdown("---")
        st.markdown("<div style='text-align: center; color: #808080;'><small>Desenvolvido por</small><br><b style='color: #E0E0E0;'>Arthur Carmélio</b></div>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 Chat & Texto", "📂 Analisador (Foto/Áudio)"])

    # ABA 1: CHAT
    with tab1:
        if 'chat' not in st.session_state: st.session_state['chat'] = []
        for msg in st.session_state['chat']:
            with st.chat_message(msg['role'], avatar="👤" if msg['role'] == "user" else "⚖️"):
                st.markdown(msg['content'])
        
        if prompt := st.chat_input("Digite sua dúvida..."):
            st.session_state['chat'].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Carmélio pensando..."):
                    resp = get_gemini_response(prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})
                    
                    # BOTÃO DE DOWNLOAD WORD NO CHAT
                    docx_file = criar_docx(resp)
                    st.download_button(
                        label="📄 Baixar Resposta em Word",
                        data=docx_file,
                        file_name="Resposta_Carmelio.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

    # ABA 2: UPLOAD
    with tab2:
        st.markdown("### 📤 Envie Documentos ou Áudios")
        uploaded = st.file_uploader("Arraste o arquivo aqui", type=["jpg", "png", "jpeg", "pdf", "mp3", "wav", "m4a", "ogg"])
        
        col1, col2 = st.columns([3, 1])
        with col1:
            user_instrucao = st.text_input("Instrução extra:", placeholder="Ex: Transcreva em inteiro teor...")
        with col2:
            st.write("") 
            st.write("") 
            processar = st.button("🚀 Processar", use_container_width=True)

        if uploaded and processar:
            with st.spinner("⏳ Analisando..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response(user_instrucao, file_data=bytes_data, mime_type=mime, mode=mode_map[mode])
                
                st.divider()
                st.markdown("### 📋 Resultado:")
                st.write(resp)
                
                # BOTÃO DE DOWNLOAD WORD NO UPLOAD
                docx_file = criar_docx(resp)
                st.download_button(
                    label="📄 Baixar Transcrição em Word",
                    data=docx_file,
                    file_name="Transcricao_Carmelio.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="btn_upload_word"
                )

else:
    st.error("🚫 Chave não encontrada no Secrets.")
