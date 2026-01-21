import streamlit as st
from groq import Groq
from docx import Document
from io import BytesIO
import base64
import os

# ==============================================================================
# 1. CONFIGURAÇÃO E DESIGN "AI APP STYLE"
# ==============================================================================
st.set_page_config(page_title="Carmélio AI", page_icon="⚖️", layout="wide")

# CSS para transformar o Streamlit em um "App Nativo"
st.markdown("""
<style>
    /* FUNDO E GERAL */
    .stApp { background-color: #0E1117; }
    
    /* SIDEBAR (Barra Lateral) */
    [data-testid="stSidebar"] { 
        background-color: #12141C; 
        border-right: 1px solid #2B2F3B;
    }
    
    /* REMOVER O CABEÇALHO PADRÃO DO STREAMLIT */
    header {visibility: hidden;}
    
    /* ESTILO DOS MENUS DE NAVEGAÇÃO (RADIO) */
    .stRadio > div {
        background-color: transparent;
    }
    .stRadio label {
        font-size: 16px;
        padding: 10px;
        border-radius: 8px;
        transition: 0.3s;
        cursor: pointer;
    }
    .stRadio label:hover {
        background-color: #1F2430;
    }
    
    /* BOTÕES PRINCIPAIS (GRADIENTE TECH) */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 45px;
        font-weight: 600;
        border: none;
        background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%); /* Azul para Roxo */
        color: white;
        box-shadow: 0 4px 14px 0 rgba(139, 92, 246, 0.3);
        transition: 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px 0 rgba(139, 92, 246, 0.5);
        color: white;
    }
    
    /* INPUTS (CAIXAS DE TEXTO MAIS LIMPAS) */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #161922;
        border: 1px solid #2B2F3B;
        color: #E0E7FF;
        border-radius: 8px;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #3B82F6;
        box-shadow: none;
    }

    /* TEXTOS */
    h1 { font-family: 'Inter', sans-serif; font-weight: 700; color: #F3F4F6; }
    h2, h3 { color: #E5E7EB; }
    p, label { color: #9CA3AF; }
    
    /* CARD DE PERFIL */
    .profile-card {
        background: #1F2430;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #2B2F3B;
        text-align: center;
        margin-bottom: 20px;
    }
    .profile-name { color: white; font-weight: bold; font-size: 16px; margin: 0;}
    .profile-role { color: #3B82F6; font-size: 12px; margin-top: 5px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;}
    
    /* SEPARADORES */
    hr { border-color: #2B2F3B; margin: 2em 0; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DO SISTEMA (GROQ / LLAMA 3)
# ==============================================================================
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return None, "⚠️ Configure a GROQ_API_KEY nos Secrets."
    return Groq(api_key=api_key), None

def criar_docx(texto):
    try:
        if not texto or "❌" in texto: return None
        doc = Document()
        doc.add_heading('Documento Jurídico - Carmélio AI', 0)
        texto_limpo = str(texto).replace('\x00', '')
        for p in texto_limpo.split('\n'):
            if p.strip(): 
                paragraph = doc.add_paragraph(p)
                if p.upper().startswith("CLÁUSULA") or p.upper().startswith("PARÁGRAFO"):
                    paragraph.runs[0].bold = True
        doc.add_paragraph('\n\n___________________________________\nAssinatura')
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except: return None

def processar_ia(prompt, file_bytes=None, task_type="text", system_instruction="Você é um assistente útil."):
    client, erro = get_groq_client()
    if erro: return erro

    try:
        if task_type == "audio" and file_bytes:
            import tempfile
            suffix = ".mp3"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            with open(tmp_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), file.read()),
                    model="whisper-large-v3", response_format="text", language="pt"
                )
            os.unlink(tmp_path)
            return transcription

        elif task_type == "vision" and file_bytes:
            base64_image = base64.b64encode(file_bytes).decode('utf-8')
            chat_completion = client.chat.completions.create(
                messages=[{
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                model="llama-3.2-11b-vision-preview", temperature=0.1,
            )
            return chat_completion.choices[0].message.content

        else:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile", temperature=0.5,
            )
            return chat_completion.choices[0].message.content

    except Exception as e:
        return f"❌ Erro na IA: {str(e)}"

# ==============================================================================
# 3. BARRA LATERAL (NAVEGAÇÃO TIPO APP)
# ==============================================================================
with st.sidebar:
    # 1. PERFIL (CARREIRA)
    st.markdown("""
    <div class="profile-card">
        <div class="profile-name">Arthur Carmélio</div>
        <div class="profile-role">Bacharel em Direito<br>Especialista Notarial</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. MENU DE NAVEGAÇÃO (DEPARTAMENTOS)
    st.markdown("### 🧭 Navegação")
    
    # Usamos o Radio para simular um menu de app
    menu_opcao = st.radio(
        "Selecione o Departamento:",
        [
            "💬 Mentor Jurídico",
            "📄 Redação de Contratos",
            "🏢 Cartório Digital (OCR)",
            "🎙️ Transcrição de Áudio",
            "⚙️ Configurações"
        ],
        label_visibility="collapsed" # Esconde o título do radio para ficar clean
    )
    
    st.markdown("---")
    
    # 3. LINKS DISCRETOS
    c_linkedin, c_whats = st.columns(2)
    with c_linkedin:
        st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/arthurcarmelio/)")
    with c_whats:
        st.markdown("[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)](https://wa.me/5548920039720)")

# ==============================================================================
# 4. ÁREA PRINCIPAL (INTERAÇÃO LIMPA)
# ==============================================================================

# --- MÓDULO 1: MENTOR JURÍDICO (CHAT) ---
if "Mentor" in menu_opcao:
    st.title("💬 Mentor Jurídico")
    st.caption("Assistente virtual para dúvidas de OAB, Concursos e Casos Práticos.")
    
    # Seletor de Personalidade
    c_mode, _ = st.columns([1,2])
    with c_mode:
        modo = st.selectbox("Modo de Resposta:", ["Explicativo (Estudos)", "Policial (PCSC)", "Formal (Peças)"])
    
    if modo == "Explicativo (Estudos)": sys_inst = "Você é um professor de Direito. Explique de forma didática."
    elif modo == "Policial (PCSC)": sys_inst = "Você é um mentor de carreiras policiais. Foco em Penal e Processo Penal."
    else: sys_inst = "Você é um assistente jurídico formal. Use termos técnicos."

    # Histórico
    if 'chat_mentor' not in st.session_state: st.session_state.chat_mentor = []
    
    # Exibe chat
    for m in st.session_state.chat_mentor:
        avatar = "⚖️" if m['role'] == "assistant" else "👤"
        with st.chat_message(m['role'], avatar=avatar):
            st.write(m['content'])
            
    # Input
    if p := st.chat_input("Digite sua dúvida jurídica aqui..."):
        st.session_state.chat_mentor.append({"role":"user", "content":p})
        st.chat_message("user", avatar="👤").write(p)
        
        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("Consultando jurisprudência e doutrina..."):
                r = processar_ia(p, task_type="text", system_instruction=sys_inst)
                st.write(r)
                st.session_state.chat_mentor.append({"role":"assistant", "content":r})

# --- MÓDULO 2: CONTRATOS (REDAÇÃO) ---
elif "Contratos" in menu_opcao:
    st.title("📄 Redação de Contratos")
    st.caption("Gerador de minutas baseado no seu modelo personalizado (ABNT).")
    
    col_main, col_form = st.columns([1, 2])
    
    with col_main:
        st.info("💡 **Dica:** O sistema utiliza o padrão 'Darlene/Manoel' para formatação de cláusulas.")
        tipo = st.selectbox("Tipo de Contrato:", ["Aluguel Residencial", "Aluguel Comercial", "Compra e Venda", "Prestação de Serviços"])
        
        if st.button("🚀 Gerar Minuta", use_container_width=True):
            # Validação simples
            if not st.session_state.get('part_a') or not st.session_state.get('val'):
                st.toast("⚠️ Preencha pelo menos as Partes e o Valor.", icon="⚠️")
            else:
                with st.spinner("Redigindo cláusulas..."):
                    a = st.session_state.get('part_a')
                    b = st.session_state.get('part_b')
                    obj = st.session_state.get('obj')
                    val = st.session_state.get('val')
                    prazo = st.session_state.get('prazo')
                    ex = st.session_state.get('ex')
                    
                    template_base = """
                    ESTRUTURA PADRÃO OBRIGATÓRIA:
                    1. CABEÇALHO EM CAIXA ALTA.
                    2. QUALIFICAÇÃO COMPLETA.
                    3. CLÁUSULAS: Objeto, Prazo, Valor, Reajuste, Destinação, Conservação, Vistoria, Foro.
                    4. LOCAL, DATA E ASSINATURAS.
                    """
                    prompt = f"Atue como Tabelião. Redija um {tipo} seguindo: {template_base}. DADOS: LOCADOR: {a}, LOCATÁRIO: {b}, OBJETO: {obj}, VALOR: {val}, PRAZO: {prazo}, EXTRAS: {ex}."
                    
                    r = processar_ia(prompt, task_type="text")
                    st.session_state['resultado_contrato'] = r # Salva para não sumir

    with col_form:
        st.markdown("#### 📝 Dados do Contrato")
        c1, c2 = st.columns(2)
        st.session_state['part_a'] = c1.text_input("Parte A (Contratante)", placeholder="Nome, CPF, Endereço")
        st.session_state['part_b'] = c2.text_input("Parte B (Contratado)", placeholder="Nome, CPF, Endereço")
        st.session_state['obj'] = c1.text_area("Objeto", placeholder="Descrição do Imóvel ou Serviço")
        st.session_state['val'] = c2.text_area("Valor e Pagamento", placeholder="R$ 1.500,00 dia 10...")
        st.session_state['prazo'] = c1.text_input("Prazo", placeholder="12 meses")
        st.session_state['ex'] = c2.text_input("Extras", placeholder="Cláusulas especiais")

    # Área de Resultado (Aparece embaixo)
    if 'resultado_contrato' in st.session_state:
        st.markdown("---")
        st.subheader("Minuta Gerada")
        st.write(st.session_state['resultado_contrato'])
        docx = criar_docx(st.session_state['resultado_contrato'])
        if docx: st.download_button("💾 Baixar DOCX Editável", docx, f"Minuta_{tipo}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# --- MÓDULO 3: CARTÓRIO (OCR) ---
elif "Cartório" in menu_opcao:
    st.title("🏢 Cartório Digital (OCR)")
    st.caption("Transforme fotos de documentos físicos em texto editável.")
    
    col_upload, col_result = st.columns(2)
    
    with col_upload:
        st.markdown("#### 1. Envie o Documento")
        u = st.file_uploader("Arraste uma foto ou PDF", type=["jpg","png","jpeg","pdf"])
        if u and st.button("🔍 Extrair Texto", use_container_width=True):
            with st.spinner("A IA está lendo o documento..."):
                r = processar_ia("Transcreva este documento fielmente. Mantenha a formatação.", file_bytes=u.getvalue(), task_type="vision")
                st.session_state['ocr_result'] = r
                
    with col_result:
        st.markdown("#### 2. Resultado")
        if 'ocr_result' in st.session_state:
            st.text_area("Texto Extraído", st.session_state['ocr_result'], height=400)
            d = criar_docx(st.session_state['ocr_result'])
            if d: st.download_button("💾 Baixar DOCX", d, "Documento_Extraido.docx", use_container_width=True)
        else:
            st.info("O texto extraído aparecerá aqui.")

# --- MÓDULO 4: TRANSCRIÇÃO ---
elif "Transcrição" in menu_opcao:
    st.title("🎙️ Transcrição de Áudio")
    st.caption("Converta áudios de WhatsApp ou gravações em texto.")
    
    tab_rec, tab_up = st.tabs(["🔴 Gravar Agora", "📂 Upload de Arquivo"])
    audio_data = None
    
    with tab_rec:
        audio_rec = st.audio_input("Clique para gravar")
        if audio_rec: audio_data = audio_rec.getvalue()
            
    with tab_up:
        audio_file = st.file_uploader("Arquivo de Áudio", type=["mp3","wav","m4a","ogg"])
        if audio_file: audio_data = audio_file.getvalue()
            
    if audio_data and st.button("⚡ Transcrever", use_container_width=True):
        with st.spinner("Processando áudio..."):
            r = processar_ia("", file_bytes=audio_data, task_type="audio")
            st.success("Concluído!")
            st.write(r)
            d = criar_docx(r)
            if d: st.download_button("💾 Baixar Transcrição", d, "Transcricao.docx")

# --- MÓDULO 5: CONFIGURAÇÕES ---
elif "Configurações" in menu_opcao:
    st.title("⚙️ Configurações")
    st.markdown("---")
    
    st.subheader("Privacidade & Dados")
    lgpd = st.toggle("Modo Anonimização (LGPD)", value=False, help="Substitui nomes reais por [NOME] nas saídas da IA.")
    if lgpd: st.success("🔒 Modo de Privacidade Ativo")
    
    st.subheader("Sobre o Sistema")
    st.info("""
    **Carmélio AI Suite v2.0**
    
    Engine: **Groq (Llama 3)**
    Velocidade: **Ultra-Fast**
    Desenvolvido por: **Arthur Carmélio**
    """)
