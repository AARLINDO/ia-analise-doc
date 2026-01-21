import streamlit as st
import os
import tempfile
from groq import Groq
from datetime import datetime
from fpdf import FPDF
import base64
import yt_dlp
import graphviz # Certifique-se que está no requirements.txt

# ==============================================================================
# 1. CONFIGURAÇÕES VISUAIS (INTERFACE EM PORTUGUÊS)
# ==============================================================================
st.set_page_config(
    page_title="Carmélio AI Studio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    
    /* Botões com degradê elegante */
    .stButton>button {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        color: white; border: none; border-radius: 8px; height: 45px;
        font-weight: 600;
    }
    
    /* Ajuste das Abas */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; font-size: 16px; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #4facfe; border-bottom: 2px solid #4facfe; }

    /* Tela de Boas-vindas Centralizada */
    .welcome-container {
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        height: 50vh; 
        text-align: center;
        color: #E0E0E0;
    }
    .welcome-icon { font-size: 80px; margin-bottom: 20px; }
    .welcome-text { font-size: 32px; font-weight: 700; margin-bottom: 10px; }
    .welcome-sub { font-size: 18px; color: #888; }
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
        # Tratamento para acentos em Português no PDF
        safe_content = content.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 7, safe_content)
        return pdf.output(dest='S').encode('latin-1')

class GroqService:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        self.model_name = "llama-3.3-70b-versatile"

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
                    {"type": "text", "text": "Transcreva todo o texto desta imagem para Português. Se for documento jurídico, mantenha a formatação exata."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            model="llama-3.2-11b-vision-preview",
            temperature=0.1,
        )
        return response.choices[0].message.content

    def chat_response(self, history):
        clean_messages = []
        for msg in history:
            if isinstance(msg, dict) and msg.get("content") and str(msg["content"]).strip():
                clean_messages.append({"role": msg["role"], "content": str(msg["content"])})
        
        if not clean_messages: return "Erro: Mensagem vazia enviada."

        try:
            response = self.client.chat.completions.create(
                messages=clean_messages,
                model=self.model_name,
                temperature=0.5,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Erro na IA: {str(e)}"

    def analyze_text(self, text, mode):
        prompts = {
            "resumo": "Atue como um assistente jurídico brasileiro. Faça um resumo executivo detalhado em Português do Brasil.",
            "ata": "Reescreva o texto abaixo no formato formal de uma Ata Notarial conforme as normas dos cartórios brasileiros.",
            "peticao": "Estruture os fatos abaixo como uma Petição Inicial (Endereçamento, Fatos, Direito, Pedidos) conforme o CPC/2015 brasileiro.",
            "estrategia": "Atue como professor do Estratégia Concursos. Crie um GUIA DE PEÇA PRÁTICA em Português com: 1. Endereçamento/Qualificação, 2. Fatos (Resumo), 3. Do Direito (Silepse), 4. Pedidos, 5. Dicas da Banca (FGV/Cebraspe)."
        }
        sys_msg = prompts.get(mode, prompts["resumo"])
        response = self.client.chat.completions.create(
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": text}],
            model=self.model_name
        )
        return response.choices[0].message.content

    def generate_flowchart(self, text):
        prompt = f"""
        Crie um código GRAPHVIZ (DOT) válido que represente o passo a passo lógico jurídico do texto abaixo.
        Use textos em Português dentro dos nós.
        Retorne APENAS o código DOT.
        Texto: {text[:10000]}
        """
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model_name
        )
        code = response.choices[0].message.content
        return code.replace("```dot", "").replace("```", "").strip()

# ==============================================================================
# 3. INTERFACE PRINCIPAL
# ==============================================================================
if 'transcription_text' not in st.session_state: st.session_state['transcription_text'] = ""
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []

SYSTEM_API_KEY = st.secrets.get("GROQ_API_KEY", None)

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("### ⚙️ Carmélio AI")
    if SYSTEM_API_KEY:
        st.success("✅ Sistema Conectado")
        api_key = SYSTEM_API_KEY
    else:
        st.warning("⚠️ Chave não detectada")
        api_key = st.text_input("Cole sua API Key:", type="password")
    
    st.divider()
    if st.button("🗑️ Nova Sessão / Limpar"):
        st.session_state['transcription_text'] = ""
        st.session_state['chat_history'] = []
        st.rerun()
    
    # --- CRÉDITOS ---
    st.divider()
    st.markdown("""
    <div style='text-align: center; font-size: 12px; color: #888;'>
        Desenvolvido por<br>
        <strong>Arthur Carmélio</strong>
    </div>
    """, unsafe_allow_html=True)

st.markdown("## ⚖️ Carmélio AI Studio")
tab1, tab2, tab3, tab4 = st.tabs(["📂 Mídia & Arquivos", "💬 Chat Assistente", "🛠️ Gerador de Peças", "📺 YouTube (Estudos)"])

# --- ABA 1: MÍDIA ---
with tab1:
    col_up, col_cam = st.columns(2)
    with col_up:
        st.markdown("#### 📤 Upload de Arquivos")
        f = st.file_uploader("Arraste áudios ou vídeos aqui", type=["mp3","m4a","wav","ogg"])
        if f and st.button("Transcrever Áudio"):
            if not api_key: st.error("Configure a API Key na barra lateral.")
            else:
                with st.spinner("Ouvindo e transcrevendo..."):
                    groq = GroqService(api_key)
                    suffix = f".{f.name.split('.')[-1]}"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(f.getvalue())
                        path = tmp.name
                    st.session_state['transcription_text'] = groq.transcribe_audio(path)
                    os.unlink(path)
                    st.success("Transcrição concluída!")

    with col_cam:
        st.markdown("#### 📸 Digitalizar Documento")
        cam = st.camera_input("Tire uma foto do documento")
        if cam and st.button("Ler e Digitalizar"):
            if not api_key: st.error("Configure a API Key.")
            else:
                with st.spinner("Lendo documento com IA..."):
                    groq = GroqService(api_key)
                    st.session_state['transcription_text'] = groq.analyze_image(cam.getvalue())
                    st.success("Leitura concluída!")

    if st.session_state['transcription_text']:
        with st.expander("Ver Texto Extraído", expanded=True):
            st.text_area("Conteúdo:", st.session_state['transcription_text'], height=200)

# --- ABA 2: CHAT (VISUAL GEMINI) ---
with tab2:
    if not st.session_state['chat_history']:
        st.markdown("""
        <div class='welcome-container'>
            <div class='welcome-icon'>⚖️</div>
            <div class='welcome-text'>Olá, Arthur.</div>
            <div class='welcome-sub'>Como posso ajudar com seus processos hoje?</div>
        </div>
        """, unsafe_allow_html=True)
        
        cols = st.columns(3)
        if cols[0].button("📝 Resumir caso"): 
            st.session_state['chat_history'].append({"role": "user", "content": "Faça um resumo detalhado deste caso."})
            st.rerun()
        if cols[1].button("📜 Criar Minuta"):
            st.session_state['chat_history'].append({"role": "user", "content": "Crie uma minuta jurídica com base nisso."})
            st.rerun()
        if cols[2].button("🔍 Analisar Riscos"):
             st.session_state['chat_history'].append({"role": "user", "content": "Quais são os riscos jurídicos aqui?"})
             st.rerun()

    for m in st.session_state['chat_history']:
        avatar = "👤" if m["role"] == "user" else "⚖️"
        st.chat_message(m["role"], avatar=avatar).markdown(m["content"])
    
    if p := st.chat_input("Digite sua dúvida jurídica ou comando..."):
        if not api_key: st.error("Conecte a API Key.")
        else:
            st.session_state['chat_history'].append({"role": "user", "content": p})
            st.chat_message("user", avatar="👤").markdown(p)
            with st.chat_message("assistant", avatar="⚖️"):
                with st.spinner("Consultando base jurídica..."):
                    groq = GroqService(api_key)
                    contexto = f"CONTEXTO DO DOCUMENTO: {st.session_state['transcription_text']}" if st.session_state['transcription_text'] else ""
                    msgs = [{"role": "system", "content": f"Você é o Carmélio AI, um assistente jurídico especialista na legislação brasileira. Responda sempre em Português do Brasil. {contexto}"}] + st.session_state['chat_history']
                    resp = groq.chat_response(msgs)
                    st.markdown(resp)
            st.session_state['chat_history'].append({"role": "assistant", "content": resp})
            st.rerun()

# --- ABA 3: DOCS ---
with tab3:
    st.markdown("#### 🛠️ Ferramentas de Cartório e Advocacia")
    c1, c2, c3 = st.columns(3)
    mode = None
    if c1.button("📝 Gerar Resumo"): mode = "resumo"
    if c2.button("⚖️ Minuta Ata Notarial"): mode = "ata"
    if c3.button("📜 Petição Inicial (CPC)"): mode = "peticao"
    
    if mode and st.session_state['transcription_text']:
        with st.spinner("Redigindo documento..."):
            groq = GroqService(api_key)
            res = groq.analyze_text(st.session_state['transcription_text'], mode)
            st.write(res)
            pdf = PDFGenerator().create_report(mode.upper(), res)
            st.download_button("⬇️ Baixar PDF", data=bytes(pdf), file_name="documento_juridico.pdf", mime="application/pdf")
    elif mode:
        st.info("Primeiro faça upload de um áudio ou documento na Aba 1.")

# --- ABA 4: YOUTUBE ---
with tab4:
    st.markdown("### 🎓 Modo Estratégia: Videoaula -> Peça + Fluxograma")
    url = st.text_input("Cole o link da aula do YouTube aqui:")
    
    if url and st.button("🚀 Processar Aula"):
        if not api_key: st.error("Configure a API Key.")
        else:
            status = st.status("Baixando áudio da aula...", expanded=True)
            try:
                ydl_opts = {'format': 'bestaudio/best', 'outtmpl': '%(id)s.%(ext)s', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}], 'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    audio_file = f"{info['id']}.mp3"
                
                status.update(label="Transcrevendo aula (isso pode demorar)...", state="running")
                groq = GroqService(api_key)
                text_yt = groq.transcribe_audio(audio_file)
                if os.path.exists(audio_file): os.unlink(audio_file)
                
                status.update(label="Gerando Guia de Estudo...", state="running")
                guia = groq.analyze_text(text_yt, "estrategia")
                
                status.update(label="Desenhando Fluxograma...", state="running")
                dot_code = groq.generate_flowchart(guia)
                
                status.update(label="Concluído!", state="complete", expanded=False)
                
                col_y1, col_y2 = st.columns([1, 1])
                with col_y1:
                    st.subheader("📝 Guia da Peça")
                    st.write(guia)
                    st.download_button("Baixar Resumo (.txt)", guia, "aula_estrategia.txt")
                with col_y2: # <--- AQUI ESTAVA O ERRO (Faltava os dois pontos)
                    st.subheader("🔄 Fluxo Lógico")
                    try:
                        st.graphviz_chart(dot_code)
                    except:
                        st.warning("O fluxograma não pôde ser gerado visualmente, mas o resumo está ao lado.")
                    
            except Exception as e:
                status.update(label="Erro!", state="error")
                st.error(f"Ocorreu um erro: {str(e)}")

