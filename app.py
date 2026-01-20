import streamlit as st
import os
import tempfile
from groq import Groq
from datetime import datetime
from fpdf import FPDF
import base64
import yt_dlp # Nova ferramenta para YouTube

# ==============================================================================
# 1. CONFIGURAÇÕES VISUAIS
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
    .stButton>button {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        color: white; border: none; border-radius: 8px; height: 45px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #4facfe; border-bottom: 2px solid #4facfe; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CLASSES DE SERVIÇO
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
        # MODELO ATUALIZADO (Llama 3.3)
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
                    {"type": "text", "text": "Transcreva este documento jurídico mantendo a formatação."},
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
        
        if not clean_messages: return "Erro: Mensagem vazia."

        try:
            response = self.client.chat.completions.create(
                messages=clean_messages,
                model=self.model_name, # Usa o modelo novo configurado no init
                temperature=0.5,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Erro na IA: {str(e)}"

    def analyze_text(self, text, mode):
        prompts = {
            "resumo": "Faça um resumo executivo jurídico detalhado.",
            "ata": "Reescreva como uma Ata Notarial formal.",
            "peticao": "Estruture como Petição Inicial (Fatos, Direito, Pedidos).",
            "estrategia": "Atue como professor do Estratégia Concursos. Crie um GUIA DE PEÇA PRÁTICA com: 1. Endereçamento/Qualificação, 2. Fatos (Resumo), 3. Do Direito (Silepse: Premissa Maior/Menor/Conclusão), 4. Pedidos Taxativos, 5. Dicas da Banca (FGV)."
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
        Use formas retangulares (box) para ações e losangos (diamond) para decisões.
        Retorne APENAS o código DOT, começando com 'digraph G {{'. Sem markdown.
        Texto: {text[:10000]}
        """
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model_name
        )
        code = response.choices[0].message.content
        return code.replace("```dot", "").replace("```", "").strip()

# ==============================================================================
# 3. INTERFACE
# ==============================================================================
if 'transcription_text' not in st.session_state: st.session_state['transcription_text'] = ""
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []

# Autenticação
SYSTEM_API_KEY = st.secrets.get("GROQ_API_KEY", None)

with st.sidebar:
    st.markdown("### ⚙️ Carmélio AI")
    if SYSTEM_API_KEY:
        st.success("✅ Conectado")
        api_key = SYSTEM_API_KEY
    else:
        api_key = st.text_input("API Key:", type="password")
    
    if st.button("🗑️ Limpar Sessão"):
        st.session_state['transcription_text'] = ""
        st.session_state['chat_history'] = []
        st.rerun()

# Abas
st.markdown("## ⚖️ Carmélio AI Studio")
tab1, tab2, tab3, tab4 = st.tabs(["📂 Mídia", "💬 Chat", "🛠️ Docs", "📺 YouTube (Estudos)"])

# --- ABA 1: MÍDIA ---
with tab1:
    col_up, col_cam = st.columns(2)
    with col_up:
        f = st.file_uploader("Áudio/Vídeo", type=["mp3","m4a","wav","ogg"])
        if f and st.button("Transcrever"):
            if not api_key: st.error("Sem chave.")
            else:
                with st.spinner("Ouvindo..."):
                    groq = GroqService(api_key)
                    suffix = f".{f.name.split('.')[-1]}"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(f.getvalue())
                        path = tmp.name
                    st.session_state['transcription_text'] = groq.transcribe_audio(path)
                    os.unlink(path)
                    st.success("Pronto!")

    with col_cam:
        cam = st.camera_input("Foto Documento")
        if cam and st.button("Ler Foto"):
            if not api_key: st.error("Sem chave.")
            else:
                with st.spinner("Lendo..."):
                    groq = GroqService(api_key)
                    st.session_state['transcription_text'] = groq.analyze_image(cam.getvalue())
                    st.success("Lido!")

    if st.session_state['transcription_text']:
        with st.expander("Ver Texto Extraído", expanded=True):
            st.text_area("Texto:", st.session_state['transcription_text'], height=200)

# --- ABA 2: CHAT ---
with tab2:
    for m in st.session_state['chat_history']:
        st.chat_message(m["role"]).markdown(m["content"])
    
    if p := st.chat_input("Dúvida ou comando..."):
        if not api_key: st.error("Sem chave.")
        else:
            st.session_state['chat_history'].append({"role": "user", "content": p})
            st.chat_message("user").markdown(p)
            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    groq = GroqService(api_key)
                    msgs = [{"role": "system", "content": f"Contexto: {st.session_state['transcription_text']}"}] + st.session_state['chat_history']
                    resp = groq.chat_response(msgs)
                    st.markdown(resp)
            st.session_state['chat_history'].append({"role": "assistant", "content": resp})

# --- ABA 3: DOCS ---
with tab3:
    c1, c2, c3 = st.columns(3)
    mode = None
    if c1.button("📝 Resumo"): mode = "resumo"
    if c2.button("⚖️ Ata Notarial"): mode = "ata"
    if c3.button("📜 Petição"): mode = "peticao"
    
    if mode and st.session_state['transcription_text']:
        with st.spinner("Gerando..."):
            groq = GroqService(api_key)
            res = groq.analyze_text(st.session_state['transcription_text'], mode)
            st.write(res)
            pdf = PDFGenerator().create_report(mode.upper(), res)
            st.download_button("Baixar PDF", data=bytes(pdf), file_name="doc.pdf", mime="application/pdf")

# --- ABA 4: YOUTUBE (NOVA!) ---
with tab4:
    st.markdown("### 🎓 Modo Estratégia: Videoaula -> Peça + Fluxograma")
    url = st.text_input("Cole o link do YouTube aqui:")
    
    if url and st.button("🚀 Processar Aula"):
        if not api_key: st.error("Sem chave.")
        else:
            status = st.status("Baixando áudio do YouTube...", expanded=True)
            try:
                # 1. Download
                ydl_opts = {'format': 'bestaudio/best', 'outtmpl': '%(id)s.%(ext)s', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}], 'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    audio_file = f"{info['id']}.mp3"
                
                # 2. Transcrição
                status.update(label="Transcrevendo (pode demorar)...", state="running")
                groq = GroqService(api_key)
                # Corta para 25MB (limite aproximado) se for muito grande, ou usa pydub futuramente
                text_yt = groq.transcribe_audio(audio_file)
                if os.path.exists(audio_file): os.unlink(audio_file)
                
                # 3. Análise Estratégia
                status.update(label="Gerando Guia de Peça...", state="running")
                guia = groq.analyze_text(text_yt, "estrategia")
                
                # 4. Fluxograma
                status.update(label="Desenhando Fluxograma...", state="running")
                dot_code = groq.generate_flowchart(guia)
                
                status.update(label="Concluído!", state="complete", expanded=False)
                
                # Exibição
                col_y1, col_y2 = st.columns([1, 1])
                with col_y1:
                    st.subheader("📝 Guia da Peça")
                    st.write(guia)
                    st.download_button("Baixar Resumo", guia, "aula_estrategia.txt")
                with col_y2:
                    st.subheader("🔄 Fluxo Lógico")
                    st.graphviz_chart(dot_code)
                    
            except Exception as e:
                status.update(label="Erro!", state="error")
                st.error(f"Erro: {str(e)}")
