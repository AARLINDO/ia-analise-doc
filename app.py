import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÃO VISUAL & ESTILO
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Mobile", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background: linear-gradient(90deg, #4285F4, #9B72CB); color: white; border: none; font-weight: bold; height: 50px; }
    h1, h2, h3 { color: #E0E0E0; }
    .stSuccess, .stInfo, .stWarning { border-radius: 8px; }
    .stFileUploader { padding: 10px; border: 1px dashed #4285F4; border-radius: 10px; }
    /* Ajuste para celular */
    div[data-testid="stAudioInput"] { background-color: #1e1e1e; border-radius: 10px; padding: 10px; border: 1px solid #4285F4; }
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
            Você é o Carmélio, assistente jurídico de elite (Advogado e Escrivão).
            - ÁUDIO/DITADO: Transcreva fielmente. Se for ditado de peça, formate como peça jurídica.
            - IMAGEM: Transcrição de Inteiro Teor.
            - TEXTO: Respostas diretas e fundamentadas na lei brasileira.
        """,
        "oab": "ATUE COMO: Examinador da OAB. Corrija peças e exija fundamentação (Art. 840 CLT).",
        "pcsc": "ATUE COMO: Mentor PCSC. Foque em Inquérito Policial e Prisões."
    }
    
    model_name = "gemini-flash-latest"
    
    content = []
    if file_data:
        content.append({"mime_type": mime_type, "data": file_data})
        if not prompt:
            prompt = "Transcreva este conteúdo detalhadamente (Inteiro Teor/Ditado)."
    
    if prompt: content.append(prompt)

    try:
        model = genai.GenerativeModel(model_name, system_instruction=personas[mode])
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"❌ Erro: {str(e)}"

# ==============================================================================
# 3. INTERFACE MOBILE FIRST
# ==============================================================================
st.title("⚖️ Carmélio AI")

if "GOOGLE_API_KEY" in st.secrets:
    with st.sidebar:
        st.info("📱 Modo Mobile Ativo")
        mode = st.radio("Modo:", ["🤖 Geral/Cartório", "⚖️ OAB", "🚓 PCSC"])
        mode_map = {"🤖 Geral/Cartório": "padrao", "⚖️ OAB": "oab", "🚓 PCSC": "pcsc"}
        
        if st.button("🗑️ Nova Consulta"):
            st.session_state['chat'] = []
            st.rerun()

        st.markdown("---")
        st.markdown("<div style='text-align: center; color: #808080;'><small>Dev. Arthur Carmélio</small></div>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🎤 Gravar/Falar", "💬 Chat & Upload"])

    # ABA 1: GRAVADOR RÁPIDO (Ideal para celular)
    with tab1:
        st.markdown("### 🎙️ Ditado Jurídico")
        st.caption("Clique no microfone para ditar uma peça ou certidão.")
        
        # O NOVO COMPONENTE DE ÁUDIO DO STREAMLIT
        audio_gravado = st.audio_input("Toque para gravar")
        
        if audio_gravado:
            with st.spinner("Ouvindo e transcrevendo..."):
                # Processa o áudio gravado na hora
                bytes_data = audio_gravado.getvalue()
                mime = "audio/wav" # O navegador grava em wav geralmente
                
                resp = get_gemini_response("Transcreva este ditado.", file_data=bytes_data, mime_type=mime, mode=mode_map[mode])
                
                st.success("✅ Transcrição Concluída:")
                st.write(resp)
                
                # Baixar Word
                docx = criar_docx(resp)
                st.download_button("📄 Baixar Word", docx, "Ditado.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    # ABA 2: CHAT E UPLOAD DE ARQUIVOS
    with tab2:
        # Chat
        if 'chat' not in st.session_state: st.session_state['chat'] = []
        for msg in st.session_state['chat']:
            with st.chat_message(msg['role'], avatar="👤" if msg['role'] == "user" else "⚖️"):
                st.markdown(msg['content'])
        
        if prompt := st.chat_input("Digite ou pergunte..."):
            st.session_state['chat'].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Processando..."):
                    resp = get_gemini_response(prompt, mode=mode_map[mode])
                    st.markdown(resp)
                    st.session_state['chat'].append({"role": "assistant", "content": resp})
                    
        st.markdown("---")
        # Upload Clássico
        uploaded = st.file_uploader("📎 Anexar Foto/PDF", type=["jpg", "png", "pdf", "mp3"])
        if uploaded and st.button("Analisar Anexo"):
            with st.spinner("Lendo..."):
                bytes_data = uploaded.getvalue()
                mime = uploaded.type
                resp = get_gemini_response("Analise este anexo.", file_data=bytes_data, mime_type=mime, mode=mode_map[mode])
                st.write(resp)

else:
    st.error("🚫 Chave não encontrada no Secrets.")
