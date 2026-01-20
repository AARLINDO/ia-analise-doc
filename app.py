import streamlit as st
import os
import tempfile
from groq import Groq
from datetime import datetime
from fpdf import FPDF
import base64

# ==============================================================================
# 1. CONFIGURAÇÕES VISUAIS (GEMINI STYLE)
# ==============================================================================
st.set_page_config(
    page_title="Carmélio AI",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Customizado para Interface "Clean"
st.markdown("""
<style>
    /* Remover padding excessivo do topo */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Fundo e Cores Globais */
    .stApp {
        background-color: #0E1117;
    }
    
    /* Esconder Menu Hamburger e Rodapé Padrão */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Estilização das Abas (Mais discretas) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        font-size: 16px;
        font-weight: 600;
        border: none;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #4facfe;
        border-bottom: 2px solid #4facfe;
    }
    
    /* Botões Modernos (Degradê sutil) */
    .stButton>button {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        border-radius: 12px;
        height: 45px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(42, 82, 152, 0.4);
    }
    
    /* Caixas de Texto (Sem bordas duras) */
    .stTextArea textarea {
        background-color: #1e1e1e;
        border: 1px solid #333;
        border-radius: 12px;
        color: #e0e0e0;
    }
    
    /* Cards de Métricas e Status */
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CLASSES DE SERVIÇO (BACKEND)
# ==============================================================================

class PDFGenerator:
    def create_report(self, title, content):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Carmélio AI - Documento Oficial", ln=True, align='C')
        pdf.line(10, 25, 200, 25)
        pdf.ln(20)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, title, ln=True, align='L')
        pdf.ln(5)
        pdf.set_font("Arial", size=11)
        safe_content = content.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 7, safe_content)
        return pdf.output(dest='S').encode('latin-1')

class GroqService:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)

    def transcribe_audio(self, file_path):
        with open(file_path, "rb") as file:
            return self.client.audio.transcriptions.create(
                file=(os.path.basename(file_path), file.read()),
                model="whisper-large-v3",
                response_format="text",
                language="pt"
            )

    def analyze_image(self, image_bytes):
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        response = self.client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Transcreva todo o texto desta imagem. Se for documento jurídico, mantenha a formatação."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            model="llama-3.2-11b-vision-preview",
            temperature=0.1,
        )
        return response.choices[0].message.content

    # --- AQUI ESTÁ A CORREÇÃO QUE RESOLVE O ERRO ---
    def chat_response(self, history):
        """
        Função corrigida para limpar mensagens antes de enviar e evitar BadRequestError.
        """
        clean_messages = []
        for msg in history:
            # O Segredo: Filtra mensagens vazias ou sem conteúdo
            if isinstance(msg, dict) and msg.get("content") and str(msg["content"]).strip():
                clean_messages.append({
                    "role": msg["role"],
                    "content": str(msg["content"])
                })

        if not clean_messages:
            return "Erro: Nenhuma mensagem válida para enviar à IA."

        try:
            response = self.client.chat.completions.create(
                messages=clean_messages,
                model="llama3-70b-8192",
                temperature=0.5,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Erro na IA: {str(e)}"
    # --- FIM DA CORREÇÃO ---

    def analyze_text(self, text, mode):
        prompts = {
            "resumo": "Faça um resumo executivo jurídico detalhado do texto abaixo.",
            "ata": "Reescreva o texto abaixo no formato formal de uma Ata Notarial.",
            "peticao": "Estruture os fatos abaixo como uma Petição Inicial (Fatos, Direito, Pedidos)."
        }
        sys_msg = prompts.get(mode, prompts["resumo"])
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": text}
            ],
            model="llama3-70b-8192"
        )
        return response.choices[0].message.content

# ==============================================================================
# 3. ESTADO E CONFIGURAÇÃO
# ==============================================================================
if 'transcription_text' not in st.session_state: st.session_state['transcription_text'] = ""
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []

# Tenta pegar a chave automaticamente
SYSTEM_API_KEY = st.secrets.get("GROQ_API_KEY", None)

# ==============================================================================
# 4. SIDEBAR (MINIMALISTA)
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Ajustes")
    
    # Lógica Inteligente da Chave API
    if SYSTEM_API_KEY:
        st.success("✅ Sistema Conectado")
        api_key = SYSTEM_API_KEY
    else:
        st.warning("⚠️ Chave não detectada")
        api_key = st.text_input("Cole sua API Key:", type="password")
    
    st.divider()
    
    # Botão de Limpeza Discreto
    if st.button("Nova Sessão / Limpar"):
        st.session_state['transcription_text'] = ""
        st.session_state['chat_history'] = []
        st.rerun()
        
    st.divider()
    # Créditos atualizados conforme solicitado
    st.markdown("<div style='text-align: center; color: #666; font-size: 12px;'>Desenvolvido por<br><b>Arthur Carmélio</b></div>", unsafe_allow_html=True)

# ==============================================================================
# 5. ÁREA PRINCIPAL
# ==============================================================================

# Cabeçalho Estilo Chat
st.markdown("## Olá, Arthur. O que vamos analisar hoje?")

# Layout de Abas mais limpo
tab_media, tab_chat, tab_tools = st.tabs(["📂 Mídia & Upload", "💬 Chat Assistente", "🛠️ Ferramentas"])

# --- ABA 1: MÍDIA ---
with tab_media:
    col_upload, col_cam = st.columns(2)
    
    with col_upload:
        st.markdown("#### 📤 Arquivos")
        uploaded_file = st.file_uploader("Solte áudio ou vídeo aqui", type=["mp3", "m4a", "wav", "ogg"])
        if uploaded_file and st.button("Transcrever Arquivo"):
            if not api_key:
                st.error("Configure a API Key.")
            else:
                with st.spinner("Processando áudio..."):
                    groq_svc = GroqService(api_key)
                    # Processamento Temp
                    suffix = f".{uploaded_file.name.split('.')[-1]}"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    text = groq_svc.transcribe_audio(tmp_path)
                    st.session_state['transcription_text'] = text
                    os.unlink(tmp_path)
                    st.toast("Transcrição concluída!", icon="🎉")

    with col_cam:
        st.markdown("#### 📸 Câmera")
        camera_file = st.camera_input("Digitalizar Documento")
        if camera_file and st.button("Processar Foto"):
            if not api_key: st.error("Falta API Key")
            else:
                with st.spinner("Lendo documento..."):
                    groq_svc = GroqService(api_key)
                    text = groq_svc.analyze_image(camera_file.getvalue())
                    st.session_state['transcription_text'] = text
                    st.toast("Documento digitalizado!", icon="📄")

    # Exibição do Texto Extraído (Expansível para não poluir)
    if st.session_state['transcription_text']:
        with st.expander("Ver Conteúdo Extraído", expanded=True):
            st.text_area("Conteúdo Base:", st.session_state['transcription_text'], height=200)

# --- ABA 2: CHAT (GEMINI STYLE) ---
with tab_chat:
    # Se não tiver conteúdo, mostra mensagem de boas vindas
    if not st.session_state['transcription_text']:
        st.info("💡 Dica: Faça upload de um áudio ou foto na primeira aba para dar contexto ao Chat.")
    
    # Container das mensagens
    chat_container = st.container()
    
    with chat_container:
        for msg in st.session_state['chat_history']:
            avatar = "👤" if msg["role"] == "user" else "✨"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])
    
    # Input fixo no fundo (Estilo WhatsApp/Gemini)
    if prompt := st.chat_input("Pergunte sobre o documento ou peça uma petição..."):
        if not api_key:
            st.error("Conecte a API Key primeiro.")
        else:
            # 1. Usuário
            st.session_state['chat_history'].append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(prompt)
            
            # 2. Resposta IA
            with chat_container:
                with st.chat_message("assistant", avatar="✨"):
                    with st.spinner("Gerando resposta..."):
                        groq_svc = GroqService(api_key)
                        
                        # Monta contexto
                        messages = [
                            {"role": "system", "content": "Você é o Carmélio AI. Responda de forma profissional e jurídica."},
                            {"role": "system", "content": f"CONTEXTO DO CASO: {st.session_state['transcription_text']}"}
                        ]
                        messages.extend(st.session_state['chat_history'])
                        
                        # AQUI: A chamada agora é segura e não vai dar erro 400
                        response = groq_svc.chat_response(messages)
                        st.markdown(response)
                        
            st.session_state['chat_history'].append({"role": "assistant", "content": response})

# --- ABA 3: FERRAMENTAS RÁPIDAS ---
with tab_tools:
    st.markdown("#### Geradores Automáticos")
    col_t1, col_t2, col_t3 = st.columns(3)
    
    action = None
    if col_t1.button("📝 Criar Resumo"): action = "resumo"
    if col_t2.button("⚖️ Ata Notarial"): action = "ata"
    if col_t3.button("📜 Petição Inicial"): action = "peticao"
    
    if action and st.session_state['transcription_text']:
        with st.spinner("Escrevendo documento..."):
            groq_svc = GroqService(api_key)
            doc_text = groq_svc.analyze_text(st.session_state['transcription_text'], action)
            
            st.subheader("Documento Gerado")
            st.write(doc_text)
            
            # Botão Download PDF
            pdf_gen = PDFGenerator()
            pdf_bytes = pdf_gen.create_report(f"Documento Gerado: {action.upper()}", doc_text)
            st.download_button("⬇️ Baixar PDF", data=bytes(pdf_bytes), file_name="documento.pdf", mime="application/pdf")
