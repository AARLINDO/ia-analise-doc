import streamlit as st
import os
import tempfile
from groq import Groq
from datetime import datetime
from fpdf import FPDF
import base64

# ==============================================================================
# 1. CONFIGURAÇÕES GERAIS E ESTILO (CSS PRO)
# ==============================================================================
st.set_page_config(
    page_title="Carmélio AI Studio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS Avançada para parecer um Software Desktop
st.markdown("""
<style>
    /* Fundo e Fontes */
    .main {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 600;
    }
    
    /* Cards de Métricas */
    .stMetric {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3d3d3d;
    }

    /* Botões Personalizados */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 8px rgba(255, 75, 75, 0.2);
    }
    
    /* Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 5px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    
    /* Caixa de Texto */
    .stTextArea textarea {
        font-size: 16px;
        line-height: 1.5;
        background-color: #1c1c1c;
        border: 1px solid #4a4a4a;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CLASSES UTILITÁRIAS (ORGANIZAÇÃO DE CÓDIGO)
# ==============================================================================

class PDFGenerator:
    """Classe responsável por gerar relatórios em PDF profissionais."""
    
    def create_report(self, title, content, filename="relatorio.pdf"):
        pdf = FPDF()
        pdf.add_page()
        
        # Cabeçalho
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Carmélio AI - Relatório Jurídico", ln=True, align='C')
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
        pdf.line(10, 30, 200, 30)
        pdf.ln(20)
        
        # Título do Documento
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, title, ln=True, align='L')
        pdf.ln(5)
        
        # Conteúdo
        pdf.set_font("Arial", size=11)
        # O FPDF tem problemas com utf-8 direto, precisa tratar caracteres (simplificado aqui)
        # Em produção, usaríamos encode('latin-1', 'replace') ou fontes TTF unicode
        safe_content = content.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 7, safe_content)
        
        # Rodapé
        pdf.set_y(-15)
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 10, f'Página {pdf.page_no()}', 0, 0, 'C')
        
        return pdf.output(dest='S').encode('latin-1')

class GroqService:
    """Gerencia todas as conexões com a IA (Áudio e Texto)."""
    
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)

    def transcribe_audio(self, file_path):
        """Usa Whisper Large V3 para transcrição."""
        with open(file_path, "rb") as file:
            return self.client.audio.transcriptions.create(
                file=(os.path.basename(file_path), file.read()),
                model="whisper-large-v3",
                response_format="text",
                language="pt"
            )

    def analyze_text(self, text, mode):
        """Usa Llama-3-70b para análise jurídica avançada."""
        
        prompts = {
            "resumo": "Você é um assistente jurídico sênior. Faça um resumo executivo do seguinte texto, destacando pontos cruciais, datas e nomes.",
            "ata_notarial": "Você é um escrevente de cartório. Formate o texto a seguir como uma minuta de Ata Notarial, descrevendo fielmente os fatos narrados, com linguagem formal e objetiva.",
            "peticao": "Você é um advogado. Analise o relato abaixo e extraia: 1. Fatos Relevantes, 2. Fundamentação Jurídica sugerida (Direito Civil/Penal BR), 3. Pedidos sugeridos.",
            "correcao": "Atue como um revisor gramatical. Corrija a pontuação, ortografia e coerência do texto mantendo o tom original."
        }
        
        system_prompt = prompts.get(mode, prompts["resumo"])
        
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            model="llama3-70b-8192", # Modelo muito inteligente e rápido
            temperature=0.3, # Baixa criatividade para ser fiel aos fatos
        )
        return response.choices[0].message.content

# ==============================================================================
# 3. GERENCIAMENTO DE ESTADO (SESSION STATE ROBUSTO)
# ==============================================================================
if 'transcription_text' not in st.session_state:
    st.session_state['transcription_text'] = ""
if 'analysis_result' not in st.session_state:
    st.session_state['analysis_result'] = ""
if 'current_file_name' not in st.session_state:
    st.session_state['current_file_name'] = ""
if 'processing_log' not in st.session_state:
    st.session_state['processing_log'] = []

def add_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state['processing_log'].append(f"[{timestamp}] {message}")

# ==============================================================================
# 4. SIDEBAR - CONTROLE DE COMANDO
# ==============================================================================
with st.sidebar:
    st.title("⚙️ Painel de Controle")
    
    # API Key Handling
    api_key = st.text_input("Chave API Groq", type="password", help="Cole sua chave gsk_... aqui")
    if not api_key:
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if api_key:
            st.success("Chave carregada do sistema!", icon="🔐")
        else:
            st.warning("Insira a chave para começar.")
    
    st.divider()
    
    st.subheader("Modo de Operação")
    operation_mode = st.radio(
        "Selecione o objetivo:",
        ["Apenas Transcrever", "Gerar Resumo Jurídico", "Minuta de Ata Notarial", "Estrutura de Petição"],
        index=0
    )
    
    st.divider()
    st.info("Desenvolvido para **Arthur Carmélio** | Escrevente & Dev")
    
    if st.session_state['processing_log']:
        with st.expander("Logs do Sistema", expanded=False):
            for log in st.session_state['processing_log']:
                st.caption(log)

# ==============================================================================
# 5. INTERFACE PRINCIPAL - SISTEMA DE ABAS
# ==============================================================================
st.title("Carmélio AI Studio 🤖⚖️")
st.markdown("### Solução Integrada de Inteligência Artificial Jurídica")

tab1, tab2, tab3 = st.tabs(["📂 1. Upload & Transcrição", "🧠 2. Análise Jurídica", "📄 3. Exportação"])

# --- ABA 1: UPLOAD E TRANSCRIÇÃO ---
with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Arraste arquivos de áudio (WhatsApp, Gravações)", 
            type=["mp3", "mp4", "m4a", "wav", "ogg"]
        )
    
    with col2:
        st.write("### Status")
        if uploaded_file:
            st.success(f"Arquivo carregado: {uploaded_file.name}")
            st.metric(label="Tamanho", value=f"{uploaded_file.size / 1024:.2f} KB")
        else:
            st.info("Aguardando arquivo...")

    if uploaded_file and api_key:
        if st.button("🚀 Iniciar Processamento", type="primary"):
            try:
                groq_svc = GroqService(api_key)
                add_log("Iniciando processamento...")
                
                with st.spinner("Processando áudio com Whisper V3..."):
                    # Criar temp file
                    suffix = f".{uploaded_file.name.split('.')[-1]}"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    # Transcrever
                    text = groq_svc.transcribe_audio(tmp_path)
                    st.session_state['transcription_text'] = text
                    st.session_state['current_file_name'] = uploaded_file.name
                    add_log("Transcrição concluída com sucesso.")
                    
                    # Limpar temp
                    os.unlink(tmp_path)
                    
                    st.success("Transcrição Finalizada! Vá para a aba de Análise ou veja abaixo.")
            
            except Exception as e:
                st.error(f"Erro crítico: {e}")
                add_log(f"ERRO: {e}")

    # Exibição Rápida da Transcrição
    if st.session_state['transcription_text']:
        st.subheader("Texto Bruto Transcrito:")
        st.text_area("", st.session_state['transcription_text'], height=300, key="txt_raw")

# --- ABA 2: ANÁLISE INTELIGENTE (O "GEMINI/LLAMA") ---
with tab2:
    st.header("Refinamento e Análise Jurídica")
    
    if not st.session_state['transcription_text']:
        st.warning("⚠️ Você precisa transcrever um áudio na Aba 1 primeiro.")
    else:
        col_opt1, col_opt2 = st.columns([1, 1])
        with col_opt1:
            analise_mode = st.selectbox(
                "O que você deseja gerar?",
                ["resumo", "ata_notarial", "peticao", "correcao"],
                format_func=lambda x: x.replace("_", " ").upper()
            )
        
        with col_opt2:
            st.write("") # Spacer
            if st.button("🧠 Executar Análise com IA", type="primary"):
                with st.spinner(f"Gerando {analise_mode} com Llama 3..."):
                    try:
                        groq_svc = GroqService(api_key)
                        result = groq_svc.analyze_text(st.session_state['transcription_text'], analise_mode)
                        st.session_state['analysis_result'] = result
                        add_log(f"Análise ({analise_mode}) concluída.")
                        st.success("Análise gerada com sucesso!")
                    except Exception as e:
                        st.error(f"Erro na análise: {e}")
        
        # Exibição do Resultado da IA
        if st.session_state['analysis_result']:
            st.divider()
            st.markdown("### 📄 Documento Gerado pela IA")
            st.text_area("Resultado Editável:", st.session_state['analysis_result'], height=500)

# --- ABA 3: EXPORTAÇÃO ---
with tab3:
    st.header("Exportar Documentos")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        st.subheader("Download Texto Simples (.txt)")
        if st.session_state['transcription_text']:
            st.download_button(
                label="📥 Baixar Transcrição Bruta",
                data=st.session_state['transcription_text'],
                file_name=f"transcricao_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )
            
    with col_exp2:
        st.subheader("Download Relatório PDF (.pdf)")
        if st.session_state['analysis_result']:
            pdf_gen = PDFGenerator()
            # Gera o PDF em memória
            pdf_bytes = pdf_gen.create_report(
                title="Documento Jurídico Processado",
                content=st.session_state['analysis_result']
            )
            
            st.download_button(
                label="📥 Baixar Documento Formatado (PDF)",
                data=bytes(pdf_bytes), # type: ignore
                file_name=f"documento_juridico_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
        else:
            st.info("Gere uma análise na Aba 2 para habilitar o PDF.")

# ==============================================================================
# 6. RODAPÉ DE DEBUG (PARA VOCÊ, DESENVOLVEDOR)
# ==============================================================================
st.divider()
with st.expander("🛠️ Área do Desenvolvedor (Debug)"):
    st.write("Session State Atual:")
    st.json(
        {k: v for k, v in st.session_state.items() if k != 'processing_log'}
    )
