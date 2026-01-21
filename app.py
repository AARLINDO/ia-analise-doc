import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÃO E DESIGN "CLEAN"
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Suite", page_icon="⚖️", layout="wide")

# CSS para esconder elementos padrões e deixar com cara de App Nativo
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    /* Botões mais bonitos e largos */
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        height: 50px; 
        font-weight: bold;
        border: none;
        background-color: #262730; 
        color: white;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #4285F4; }
    
    /* Áreas de Upload */
    .stFileUploader { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px dashed #555; }
    
    /* Títulos */
    h1, h2, h3 { color: #f0f0f0; font-family: 'Sans-serif'; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #16171c; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. INTELIGÊNCIA CENTRAL
# ==============================================================================
def criar_docx(texto):
    doc = Document()
    doc.add_heading('Documento Gerado - Carmélio AI', 0)
    doc.add_paragraph(texto)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def get_gemini_response(prompt, file_data=None, mime_type=None, system_instruction=""):
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ ERRO: Chave não configurada no Secrets."

    model_name = "gemini-flash-latest" # O modelo rápido e multimodal
    
    content = []
    if file_data:
        content.append({"mime_type": mime_type, "data": file_data})
    
    if prompt: content.append(prompt)

    try:
        model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"❌ Erro no processamento: {str(e)}"

# ==============================================================================
# 3. MENU DE NAVEGAÇÃO
# ==============================================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2585/2585188.png", width=60)
    st.markdown("### Carmélio Suite")
    
    # O SEGREDO DO DESIGN: Menu de Navegação
    pagina = st.radio(
        "Navegação:", 
        ["🎓 Sala de Estudos", "🏛️ Cartório (Inteiro Teor)", "🎙️ Transcritor de Áudio"],
        index=0
    )
    
    st.divider()
    st.markdown("<small style='color: #666;'>Desenvolvido por<br><b>Arthur Carmélio</b></small>", unsafe_allow_html=True)

# ==============================================================================
# MÓDULO 1: SALA DE ESTUDOS (OAB/PCSC)
# ==============================================================================
if pagina == "🎓 Sala de Estudos":
    st.title("🎓 Mentor Jurídico")
    st.caption("Focado em OAB e Concursos PCSC")
    
    # Toggle rápido
    modo_estudo = st.selectbox("Escolha o Foco:", ["⚖️ OAB (Trabalho)", "🚓 PCSC (Escrivão)"])
    
    # Definição das Personas
    persona_oab = "Você é Examinador da OAB 2ª Fase. Corrija peças, exija Art. 840 CLT, Súmulas e OJ. Seja rigoroso."
    persona_pcsc = "Você é Mentor para Escrivão PCSC. Foque em Inquérito Policial, CPP, Prisões e pegadinhas da banca."
    
    instrucao_atual = persona_oab if "OAB" in modo_estudo else persona_pcsc

    # Chat Simples e Direto
    if 'chat_estudo' not in st.session_state: st.session_state['chat_estudo'] = []
    
    for msg in st.session_state['chat_estudo']:
        avatar = "⚖️" if msg['role'] == "assistant" else "👤"
        st.chat_message(msg['role'], avatar=avatar).write(msg['content'])
        
    if prompt := st.chat_input("Digite sua dúvida, peça uma questão ou cole sua peça..."):
        st.session_state['chat_estudo'].append({"role": "user", "content": prompt})
        st.chat_message("user", avatar="👤").write(prompt)
        
        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("O Mentor está analisando..."):
                resp = get_gemini_response(prompt, system_instruction=instrucao_atual)
                st.write(resp)
                st.session_state['chat_estudo'].append({"role": "assistant", "content": resp})

# ==============================================================================
# MÓDULO 2: CARTÓRIO (INTEIRO TEOR & OCR)
# ==============================================================================
elif pagina == "🏛️ Cartório (Inteiro Teor)":
    st.title("🏛️ Cartório Digital")
    st.info("💡 **Função:** Extrair texto de fotos de livros, certidões antigas ou PDFs.")
    
    col1, col2 = st.columns([1, 2])
    
    uploaded_file = st.file_uploader("Tire uma foto ou suba o arquivo", type=["jpg", "png", "jpeg", "pdf"])
    
    if uploaded_file:
        st.markdown("### 👀 Pré-visualização")
        # Mostra a imagem pequena para confirmar
        if "pdf" not in uploaded_file.type:
            st.image(uploaded_file, width=300)
            
        btn_processar = st.button("📝 Gerar Inteiro Teor (Extrair Texto)", type="primary")
        
        if btn_processar:
            with st.spinner("Lendo manuscritos e datilografia..."):
                persona_cartorio = """
                ATUE COMO: Oficial de Cartório Experiente.
                TAREFA: Transcrever o documento da imagem em INTEIRO TEOR (Ipsis Litteris).
                REGRAS:
                1. Não resuma. Copie cada palavra.
                2. Se houver carimbos, escreva [Carimbo: texto].
                3. Se for ilegível, escreva [ilegível].
                4. Mantenha a formatação formal de certidão.
                """
                bytes_data = uploaded_file.getvalue()
                resp = get_gemini_response("Transcreva em Inteiro Teor.", file_data=bytes_data, mime_type=uploaded_file.type, system_instruction=persona_cartorio)
                
                st.success("Transcrição Concluída!")
                st.text_area("Texto Extraído:", value=resp, height=400)
                
                # Download
                docx = criar_docx(resp)
                st.download_button("💾 Baixar Word (.docx)", docx, "Inteiro_Teor.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# ==============================================================================
# MÓDULO 3: TRANSCRITOR DE ÁUDIO
# ==============================================================================
elif pagina == "🎙️ Transcritor de Áudio":
    st.title("🎙️ Estúdio de Transcrição")
    st.caption("Ideal para: Atas, Audiências, Ditados de Peças e Notas de Voz.")
    
    tab_mic, tab_upload = st.tabs(["🔴 Gravar Agora", "📂 Subir Arquivo"])
    
    audio_data = None
    mime_audio = None
    
    # Opção 1: Microfone
    with tab_mic:
        audio_rec = st.audio_input("Clique para gravar")
        if audio_rec:
            audio_data = audio_rec.getvalue()
            mime_audio = "audio/wav"
            
    # Opção 2: Arquivo
    with tab_upload:
        audio_file = st.file_uploader("Subir MP3/WAV/M4A/OGG", type=["mp3", "wav", "m4a", "ogg"])
        if audio_file:
            audio_data = audio_file.getvalue()
            mime_audio = audio_file.type
            
    if audio_data:
        st.divider()
        st.write("Arquivo pronto para processamento.")
        tipo_transcricao = st.radio("Tipo de Saída:", ["Texto Corrido (Ditado)", "Ata Formal (Reunião/Audiência)", "Resumo em Tópicos"])
        
        if st.button("🗣️ Iniciar Transcrição"):
            with st.spinner("Ouvindo..."):
                prompts = {
                    "Texto Corrido (Ditado)": "Transcreva o áudio exatamente como foi falado, corrigindo apenas pontuação e vícios de linguagem graves.",
                    "Ata Formal (Reunião/Audiência)": "Transcreva em formato de ATA FORMAL ou TERMO DE AUDIÊNCIA. Identifique os interlocutores se possível. Use linguagem culta.",
                    "Resumo em Tópicos": "Resuma o conteúdo do áudio em tópicos principais, destacando decisões e prazos."
                }
                
                resp = get_gemini_response(prompts[tipo_transcricao], file_data=audio_data, mime_type=mime_audio)
                
                st.markdown("### 📝 Resultado:")
                st.write(resp)
                
                docx = criar_docx(resp)
                st.download_button("💾 Baixar Transcrição (.docx)", docx, "Transcricao.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
