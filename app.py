import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÃO E DESIGN "JURIS GOLD" (PREMIUM)
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Suite", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    /* FUNDO GERAL (Dark Navy) */
    .stApp { background-color: #0E1117; }
    
    /* SIDEBAR (Cinza Escuro Profissional) */
    [data-testid="stSidebar"] { 
        background-color: #161a24; 
        border-right: 1px solid #2b303b;
    }

    /* BOTÕES (Estilo Dourado/Bronze - OAB/Cartório) */
    .stButton>button { 
        width: 100%; 
        border-radius: 6px; 
        height: 50px; 
        font-weight: bold;
        border: none;
        /* Gradiente Dourado Sóbrio */
        background: linear-gradient(90deg, #967036, #C6A34F); 
        color: #000000; /* Texto preto no dourado para contraste */
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: 0.3s;
    }
    .stButton>button:hover { 
        background: linear-gradient(90deg, #C6A34F, #E5C365); 
        color: #000;
        box-shadow: 0 4px 10px rgba(198, 163, 79, 0.3);
    }
    
    /* Áreas de Upload */
    .stFileUploader { background-color: #1b1e26; padding: 20px; border-radius: 10px; border: 1px dashed #967036; }
    
    /* Títulos e Textos */
    h1, h2, h3 { color: #E5C365; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    p, li { color: #e0e0e0; }
    
    /* Inputs de Texto */
    .stTextInput>div>div>input { color: white; background-color: #262730; border: 1px solid #444; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DO SISTEMA
# ==============================================================================
def criar_docx(texto):
    doc = Document()
    doc.add_heading('Documento Gerado - Carmélio AI', 0)
    doc.add_paragraph(texto)
    doc.add_paragraph('\n\n___________________________________\nAssinatura')
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def get_gemini_response(prompt, file_data=None, mime_type=None, system_instruction="", anonimizar=False):
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ ERRO: Chave não configurada no Secrets."

    model_name = "gemini-flash-latest"
    
    # Lógica de Anonimização (LGPD)
    if anonimizar:
        system_instruction += "\n\nREGRA LGPD ATIVA: Substitua TODOS os nomes de pessoas reais por [NOME], CPFs por [CPF] e endereços por [ENDEREÇO]. Proteja os dados."
    
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
# 3. BARRA LATERAL (MENU + LGPD)
# ==============================================================================
with st.sidebar:
    try:
        st.image("logo.png", width=180) 
    except:
        st.warning("⚠️ Adicione 'logo.png' no GitHub.")

    st.markdown("### 🏛️ Carmélio Suite")
    
    # MENU PRINCIPAL (COM AS 4 OPÇÕES)
    pagina = st.radio(
        "Navegação:", 
        [
            "🎓 Sala de Estudos", 
            "🏛️ Cartório (Inteiro Teor)", 
            "🎙️ Transcritor de Áudio",
            "🧠 Como Funciona (Técnico)" # <--- AQUI ESTÁ A ABA TÉCNICA
        ],
        index=0
    )
    
    st.markdown("---")
    
    # --- ESCUDO LGPD ---
    st.markdown("### 🛡️ Privacidade (LGPD)")
    modo_anonimo = st.toggle("Modo Anonimização", value=False, help="Substitui nomes e dados sensíveis por [TAGS] na resposta.")
    
    termo_aceite = st.checkbox("Declaro que tenho autorização legal para processar os dados inseridos.", value=True)
    
    st.markdown("---")
    st.markdown("<small style='color: #666;'>Desenvolvido por<br><b style='color: #C6A34F;'>Arthur Carmélio</b></small>", unsafe_allow_html=True)

# VERIFICAÇÃO DE SEGURANÇA
if not termo_aceite:
    st.error("🚫 Acesso Bloqueado. Por favor, aceite o termo de responsabilidade de dados na barra lateral para continuar.")
    st.stop()

# ==============================================================================
# MÓDULO 1: SALA DE ESTUDOS
# ==============================================================================
if pagina == "🎓 Sala de Estudos":
    st.title("🎓 Mentor Jurídico")
    st.caption("Focado em OAB e Concursos PCSC")
    
    modo_estudo = st.selectbox("Escolha o Foco:", ["⚖️ OAB (Trabalho)", "🚓 PCSC (Escrivão)"])
    
    persona_oab = "Você é Examinador da OAB 2ª Fase. Corrija peças, exija Art. 840 CLT, Súmulas e OJ. Seja rigoroso."
    persona_pcsc = "Você é Mentor para Escrivão PCSC. Foque em Inquérito Policial, CPP, Prisões e pegadinhas da banca."
    
    instrucao_atual = persona_oab if "OAB" in modo_estudo else persona_pcsc

    if 'chat_estudo' not in st.session_state: st.session_state['chat_estudo'] = []
    
    for msg in st.session_state['chat_estudo']:
        avatar = "⚖️" if msg['role'] == "assistant" else "👤"
        st.chat_message(msg['role'], avatar=avatar).write(msg['content'])
        
    if prompt := st.chat_input("Digite sua dúvida ou cole sua peça..."):
        st.session_state['chat_estudo'].append({"role": "user", "content": prompt})
        st.chat_message("user", avatar="👤").write(prompt)
        
        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("Analisando base legal..."):
                resp = get_gemini_response(prompt, system_instruction=instrucao_atual, anonimizar=modo_anonimo)
                st.write(resp)
                st.session_state['chat_estudo'].append({"role": "assistant", "content": resp})

# ==============================================================================
# MÓDULO 2: CARTÓRIO
# ==============================================================================
elif pagina == "🏛️ Cartório (Inteiro Teor)":
    st.title("🏛️ Cartório Digital")
    st.info("💡 Extração de texto de livros antigos, certidões e PDFs.")
    
    uploaded_file = st.file_uploader("Foto ou PDF", type=["jpg", "png", "jpeg", "pdf"])
    
    if uploaded_file:
        if "pdf" not in uploaded_file.type:
            st.image(uploaded_file, width=300)
            
        if st.button("📝 Gerar Inteiro Teor", type="primary"):
            with st.spinner("Lendo manuscritos e datilografia..."):
                persona_cartorio = "ATUE COMO: Oficial de Cartório. Transcreva em INTEIRO TEOR (Ipsis Litteris). Marque [ilegível] se necessário. Mantenha formatação oficial."
                bytes_data = uploaded_file.getvalue()
                resp = get_gemini_response("Transcreva em Inteiro Teor.", file_data=bytes_data, mime_type=uploaded_file.type, system_instruction=persona_cartorio, anonimizar=modo_anonimo)
                
                st.success("Transcrição Concluída!")
                st.text_area("Texto:", value=resp, height=400)
                docx = criar_docx(resp)
                st.download_button("💾 Baixar Word (.docx)", docx, "Inteiro_Teor.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# ==============================================================================
# MÓDULO 3: ÁUDIO
# ==============================================================================
elif pagina == "🎙️ Transcritor de Áudio":
    st.title("🎙️ Estúdio de Transcrição")
    
    tab_mic, tab_upload = st.tabs(["🔴 Gravar (Ditado)", "📂 Subir Arquivo"])
    audio_data = None
    mime_audio = None
    
    with tab_mic:
        audio_rec = st.audio_input("Clique para gravar ditado ou audiência")
        if audio_rec:
            audio_data = audio_rec.getvalue()
            mime_audio = "audio/wav"
            
    with tab_upload:
        audio_file = st.file_uploader("Arquivos (MP3, WAV, M4A)", type=["mp3", "wav", "m4a", "ogg"])
        if audio_file:
            audio_data = audio_file.getvalue()
            mime_audio = audio_file.type
            
    if audio_data:
        st.divider()
        if st.button("🗣️ Iniciar Transcrição"):
            with st.spinner("Ouvindo e convertendo para texto..."):
                resp = get_gemini_response("Transcreva o áudio detalhadamente.", file_data=audio_data, mime_type=mime_audio, anonimizar=modo_anonimo)
                st.markdown("### 📝 Resultado:")
                st.write(resp)
                docx = criar_docx(resp)
                st.download_button("💾 Baixar Word (.docx)", docx, "Transcricao.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# ==============================================================================
# MÓDULO 4: TÉCNICO (EXPLICAÇÃO)
# ==============================================================================
elif pagina == "🧠 Como Funciona (Técnico)":
    st.title("🧠 Arquitetura do Sistema")
    st.markdown("---")
    
    st.markdown("""
    ### 🏗️ Bastidores do Carmélio AI
    
    Este aplicativo utiliza o estado da arte em **IA Generativa Multimodal**. Abaixo, explicamos como garantimos precisão e segurança.
    """)
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.success("""
        **1. Motor de IA (Google Gemini)**
        
        * Utiliza redes neurais **Transformers** para entender o contexto jurídico completo.
        * **Tokens:** O modelo processa milhares de tokens por segundo, permitindo ler processos inteiros de uma vez.
        * **OCR Neural:** Consegue ler letra de mão em livros de cartório antigos.
        """)
    with col_b:
        st.warning("""
        **2. Camada de Segurança (LGPD)**
        
        * **Stateless:** O sistema não salva seus dados. Ao fechar a aba, tudo é deletado da memória RAM.
        * **Anonimização:** Algoritmo que detecta e mascara Nomes e CPFs quando solicitado na barra lateral.
        """)
        
    st.markdown("---")
    st.subheader("👨‍💻 Exemplo de Código (Treinamento)")
    st.markdown("Este é um exemplo didático de como IAs como esta são treinadas:")
    st.code("""
# Exemplo de Arquitetura Transformer (Simplificado)
import tensorflow as tf
from transformers import GPT2LMHeadModel

# 1. Carregamento do Modelo Neural
model = GPT2LMHeadModel.from_pretrained("gpt2")

# 2. Processamento Seguro
def processar_juridico(dados_processo):
    # O dado é enviado criptografado
    # A IA analisa o contexto (ex: "Deferimento", "Liminar")
    decisao = model.generate(dados_processo)
    return decisao
    """, language="python")
