import streamlit as st
import streamlit.components.v1 as components
import os
import json
import base64
import time
import re
from datetime import datetime
from io import BytesIO

# =============================================================================
# 1. CONFIGURAÇÃO E DEPENDÊNCIAS
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Suíte Jurídica",
    page_icon="✨",
    layout="wide"
)

# Importações seguras (Fallback)
try: from groq import Groq
except ImportError: Groq = None

try: import pdfplumber
except ImportError: pdfplumber = None

try: import docx as docx_reader
except ImportError: docx_reader = None

try: from PIL import Image
except ImportError: Image = None

# =============================================================================
# 2. FUNÇÕES DE COMPATIBILIDADE & UTILITÁRIOS
# =============================================================================

def safe_image_show(image_path):
    if os.path.exists(image_path):
        try:
            st.image(image_path, use_container_width=True)
        except TypeError:
            st.image(image_path, use_column_width=True)

def get_audio_input(label):
    if hasattr(st, "audio_input"):
        return st.audio_input(label)
    else:
        st.warning("⚠️ Seu sistema não suporta gravação direta. Use o upload abaixo.")
        return st.file_uploader(label, type=["wav", "mp3", "m4a", "ogg"])

# =============================================================================
# 3. CSS E DESIGN
# =============================================================================
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    
    .gemini-text {
        background: -webkit-linear-gradient(45deg, #4285F4, #9B72CB, #D96570);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.2rem; margin-bottom: 10px;
    }
    
    .timer-display {
        font-family: monospace; font-size: 80px; font-weight: 700;
        color: #FFFFFF; text-shadow: 0 0 25px rgba(59, 130, 246, 0.5);
    }
    .timer-container {
        background-color: #1F2430; border-radius: 20px; padding: 20px;
        text-align: center; border: 1px solid #2B2F3B; margin: 20px auto;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 500px;
    }
    
    .footer-credits {
        text-align: center; margin-top: 40px; padding-top: 20px;
        border-top: 1px solid #2B2F3B; color: #6B7280; font-size: 12px;
    }
    .footer-name { color: #E5E7EB; font-weight: 700; font-size: 14px; display: block; margin-top: 5px; }
    
    .stButton>button { border-radius: 12px; font-weight: 600; border: none; }
    .question-card { 
        background: linear-gradient(135deg, #1F2937 0%, #111827 100%); 
        padding: 20px; border-radius: 15px; border: 1px solid #374151; margin-bottom: 10px; 
    }
    
    textarea { font-size: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 4. GESTÃO DE ESTADO
# =============================================================================
DEFAULTS = {
    "edital_text": "", "chat_history": [], "generated_questions": [], 
    "lgpd_ack": False, "last_heavy_call": 0.0,
    "pomo_state": "STOPPED", "pomo_mode": "Foco", 
    "pomo_duration": 25 * 60, "pomo_end_time": None,
    "pomo_auto_start": False
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

RATE_LIMIT_SECONDS = 2

def check_rate_limit():
    now = time.time()
    if now - st.session_state.last_heavy_call < RATE_LIMIT_SECONDS:
        return True
    return False

def mark_call():
    st.session_state.last_heavy_call = time.time()

def extract_json_safe(text):
    match = re.search(r"<json>(.*?)</json>", text, re.DOTALL)
    json_str = match.group(1) if match else None
    if not json_str:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        json_str = match.group(0) if match else None
    if json_str:
        try: return json.loads(json_str)
        except: return None
    return None

# =============================================================================
# 5. MOTOR DE IA (GROQ)
# =============================================================================
def get_client():
    try:
        api_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
        if not api_key: return None
        if Groq is None: return None
        return Groq(api_key=api_key)
    except:
        return None

def stream_text(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)

def call_ai(messages_or_prompt, file_bytes=None, type="text", system="Você é o Carmélio AI, assistente jurídico de elite.", temp=0.5):
    if check_rate_limit(): return None
    client = get_client()
    if not client: return "⚠️ Erro: API Key não configurada."
    
    mark_call()
    try:
        if type == "text":
            if isinstance(messages_or_prompt, str):
                msgs = [{"role":"system","content":system}, {"role":"user","content":messages_or_prompt}]
            else:
                msgs = [{"role":"system","content":system}] + messages_or_prompt
            r = client.chat.completions.create(messages=msgs, model="llama-3.3-70b-versatile", temperature=temp)
            return r.choices[0].message.content
            
        elif type == "vision" and file_bytes:
            b64 = base64.b64encode(file_bytes).decode('utf-8')
            r = client.chat.completions.create(
                messages=[{"role":"user","content":[{"type":"text","text":messages_or_prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}],
                model="llama-3.2-11b-vision-preview", temperature=0.1
            )
            return r.choices[0].message.content
            
        elif type == "audio" and file_bytes:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tmp.write(file_bytes); tmp_path = tmp.name
            with open(tmp_path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), f.read()),
                    model="whisper-large-v3", response_format="text", language="pt"
                )
            os.unlink(tmp_path)
            return transcription
            
    except Exception as e: return f"Erro na IA: {str(e)}"

# =============================================================================
# 6. SIDEBAR
# =============================================================================
with st.sidebar:
    safe_image_show("logo.jpg.png")
    st.markdown("---")
    menu = st.radio("Menu Principal:", 
        ["✨ Chat Inteligente", "🎯 Mestre dos Editais", "🍅 Sala de Foco", "📄 Redação Jurídica", "🏢 Cartório OCR", "🎙️ Transcrição"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    c_link, c_zap = st.columns(2)
    with c_link: st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")
    with c_zap: st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720)")
    st.markdown("""<div class="footer-credits">Desenvolvido por <br><span class="footer-name">Arthur Carmélio</span></div>""", unsafe_allow_html=True)

# LGPD
if not st.session_state.lgpd_ack:
    with st.expander("🔐 Acesso ao Sistema", expanded=True):
        st.write("Ao entrar, você concorda com o uso de IA.")
        if st.button("Entrar"):
            st.session_state.lgpd_ack = True
            st.rerun()
    st.stop()

# =============================================================================
# 7. MÓDULOS
# =============================================================================

# --- 1. CHAT INTELIGENTE ---
if menu == "✨ Chat Inteligente":
    st.markdown('<h1 class="gemini-text">Olá, Doutor(a).</h1>', unsafe_allow_html=True)
    if not st.session_state.chat_history:
        st.caption("Sou o Carmélio AI. Posso ajudar com dúvidas, peças, estudos ou jurisprudência.")
        c1, c2 = st.columns(2)
        if c1.button("📚 Explicar Conceito"):
            st.session_state.chat_history.append({"role": "user", "content": "Explique a diferença entre Prescrição e Decadência."})
            st.rerun()
        if c2.button("💡 Ideias de Tese"):
            st.session_state.chat_history.append({"role": "user", "content": "Sugira teses de defesa para crime de furto famélico."})
            st.rerun()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Digite sua mensagem..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                context_msgs = st.session_state.chat_history[-6:]
                res = call_ai(context_msgs, system="Seja um mentor jurídico preciso.")
                st.write_stream(stream_text(res))
                st.session_state.chat_history.append({"role": "assistant", "content": res})

    if st.session_state.chat_history:
        if st.button("🗑️ Limpar Conversa"):
            st.session_state.chat_history = []
            st.rerun()

# --- 2. MESTRE DOS EDITAIS ---
elif menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais")
    with st.expander("📂 Upload do Edital (Contexto)", expanded=not bool(st.session_state.edital_text)):
        file = st.file_uploader("Arraste seu PDF/DOCX", type=["pdf", "docx"])
        if file:
            with st.spinner("Lendo edital..."):
                raw = "Conteúdo..."
                if file.type == "application/pdf" and pdfplumber:
                    with pdfplumber.open(BytesIO(file.getvalue())) as pdf: raw = "".join([p.extract_text() or "" for p in pdf.pages])
                elif "word" in file.type and docx_reader:
                    doc = docx_reader.Document(BytesIO(file.getvalue()))
                    raw = "\n".join([p.text for p in doc.paragraphs])
                st.session_state.edital_text = raw
                st.success("Edital carregado! A IA usará este contexto.")
                st.rerun()
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    banca = c1.selectbox("Banca", ["FGV", "Cebraspe", "Vunesp", "FCC"])
    disc = c2.selectbox("Disciplina", ["Constitucional", "Administrativo", "Penal", "Civil"])
    assunto = c3.text_input("Assunto", "Atos Administrativos")
    if st.button("🚀 Gerar Questão Inédita", type="primary", use_container_width=True):
        with st.spinner("Criando..."):
            ctx = st.session_state.edital_text[:3000] if st.session_state.edital_text else ""
            p = f"Crie uma questão inédita (JSON). Banca: {banca}. Disciplina: {disc}. Assunto: {assunto}. Contexto Edital: {ctx}. Formato: <json>{{'enunciado':'...', 'alternativas':{{'A':'...','B':'...'}}, 'gabarito':'A', 'comentario':'...'}}</json>"
            res = call_ai(p, temp=0.5)
            data = extract_json_safe(res)
            if data: st.session_state.generated_questions.append(data)
    if st.session_state.generated_questions:
        q = st.session_state.generated_questions[-1]
        st.markdown(f"<div style='background:#1F2937;padding:20px;border-radius:10px;margin-bottom:10px;'><strong>{banca} | {disc}</strong><br><br>{q.get('enunciado')}</div>", unsafe_allow_html=True)
        for k,v in q.get("alternativas", {}).items(): st.write(f"**{k})** {v}")
        with st.expander("Ver Gabarito"):
            st.success(f"Gabarito: {q.get('gabarito')}")
            st.info(q.get("comentario"))

# --- 3. SALA DE FOCO ---
elif menu == "🍅 Sala de Foco":
    st.title("🍅 Foco & Produtividade")
    col_modes = st.columns([1,1,1])
    def set_pomo(mode, min):
        st.session_state.pomo_mode = mode
        st.session_state.pomo_duration = min * 60
        st.session_state.pomo_state = "STOPPED"
        st.session_state.pomo_end_time = None
        st.rerun()
    if col_modes[0].button("🧠 FOCO (25m)", use_container_width=True): set_pomo("Foco", 25)
    if col_modes[1].button("☕ CURTO (5m)", use_container_width=True): set_pomo("Descanso", 5)
    if col_modes[2].button("🧘 LONGO (15m)", use_container_width=True): set_pomo("Longo", 15)
    
    remaining = st.session_state.pomo_duration
    if st.session_state.pomo_state == "RUNNING":
        now = time.time()
        if now >= st.session_state.pomo_end_time:
            st.session_state.pomo_state = "STOPPED"
            st.balloons()
            if st.session_state.get("pomo_auto_start"):
                next_mode = "Descanso" if st.session_state.pomo_mode == "Foco" else "Foco"
                next_min = 5 if next_mode == "Descanso" else 25
                st.session_state.pomo_mode = next_mode
                st.session_state.pomo_duration = next_min * 60
                st.session_state.pomo_end_time = time.time() + (next_min * 60)
                st.session_state.pomo_state = "RUNNING"
                time.sleep(2)
                st.rerun()
            else: remaining = 0
        else:
            remaining = int(st.session_state.pomo_end_time - now)
            time.sleep(1)
            st.rerun()
    
    mins, secs = divmod(remaining, 60)
    st.markdown(f"<div style='text-align:center;font-size:80px;font-weight:bold;color:white;margin:20px 0;'>{mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    if c1.button("▶️ INICIAR", use_container_width=True, type="primary"):
        if st.session_state.pomo_state != "RUNNING":
            st.session_state.pomo_state = "RUNNING"
            st.session_state.pomo_end_time = time.time() + remaining
            st.rerun()
    if c2.button("⏸️ PAUSAR", use_container_width=True):
        if st.session_state.pomo_state == "RUNNING":
            st.session_state.pomo_state = "PAUSED"
            st.session_state.pomo_duration = remaining
            st.rerun()
    if c3.button("🔄 ZERAR", use_container_width=True):
        st.session_state.pomo_state = "STOPPED"
        st.session_state.pomo_duration = 25 * 60
        st.rerun()
    st.checkbox("🔄 Ciclos automáticos", key="pomo_auto_start")
    with st.expander("🎵 Rádio Lofi", expanded=False): st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")

# --- 4. REDAÇÃO JURÍDICA (VERSÃO PRO) ---
elif menu == "📄 Redação Jurídica":
    st.title("📄 Redação Jurídica")
    
    tab_ia, tab_ext = st.tabs(["✨ Gerador Carmélio (Pro)", "🔗 Integrações Externas"])
    
    # GERADOR INTERNO MELHORADO COM "DICAS DA JURIDICA AI"
    with tab_ia:
        st.info("Descreva o caso e a IA Carmélio redige a peça com estrutura de alta qualidade (Confidencialidade, LGPD, Foro, etc).")
        c1, c2 = st.columns([1, 2])
        tipo = c1.selectbox("Documento", ["Contrato de Prestação de Serviços", "Petição Inicial", "Contrato de Honorários", "Procuração Ad Judicia", "Memorando", "Notificação Extrajudicial"])
        det = c2.text_area("Fatos e Detalhes", height=150, key="redacao_detalhes", placeholder="Ex: Contratante João (CPF X), Contratado Pedro (CNPJ Y). Objeto: Desenvolvimento de Software. Valor R$ 5k.")
        
        if st.button("✍️ Gerar Documento Completo"):
            if det:
                with st.spinner("Aplicando técnica jurídica avançada..."):
                    # Prompt Baseado nas "Dicas da Jurídico AI" (Estrutura Completa)
                    prompt_pro = f"""
                    Você é um advogado sênior de um grande escritório.
                    Redija um(a) {tipo} profissional e completo com base nestes detalhes: {det}.
                    
                    ESTRUTURA OBRIGATÓRIA (Siga rigorosamente):
                    1. QUALIFICAÇÃO COMPLETA: Nome, nacionalidade, estado civil, profissão, RG, CPF, endereço. (Deixe [CAMPO] para o que faltar).
                    2. OBJETO: Descrição detalhada e técnica.
                    3. OBRIGAÇÕES: Liste obrigações específicas para Contratante e Contratado.
                    4. PREÇO E PAGAMENTO: Valor, forma, prazos, multas por atraso (juros de mora 1% a.m + multa 2%).
                    5. PRAZOS DE EXECUÇÃO: Início, fim, cronograma.
                    6. RESCISÃO: Hipóteses de justa causa, aviso prévio, multas rescisórias.
                    7. PROPRIEDADE INTELECTUAL: Cláusula de cessão de direitos (se aplicável).
                    8. CONFIDENCIALIDADE: Dever de sigilo de 5 anos (padrão de mercado).
                    9. PROTEÇÃO DE DADOS (LGPD): Cláusula de conformidade com a Lei 13.709/2018.
                    10. FORO: Eleição de foro para dirimir controvérsias.
                    
                    Use linguagem formal, culta e direta. Numere as cláusulas (1., 1.1, 1.2).
                    """
                    res = call_ai(prompt_pro, temp=0.2)
                    st.text_area("Minuta Final:", res, height=600)
            else:
                st.warning("Preencha os detalhes para gerar.")

    # FERRAMENTAS EXTERNAS
    with tab_ext:
        st.markdown("### Jurídico AI & Outros")
        st.caption("Acesse plataformas parceiras diretamente.")
        st.link_button("🔗 Abrir Jurídico AI (Contratos)", "https://app.juridico.ai/contrato")
        try:
            components.iframe("https://app.juridico.ai/contrato", height=800, scrolling=True)
        except:
            st.error("Visualização bloqueada pelo site. Use o botão acima.")

# --- 5. OCR ---
elif menu == "🏢 Cartório OCR":
    st.title("🏢 Leitor de Documentos")
    st.info("Extraia texto de imagens e PDFs.")
    u = st.file_uploader("Arquivo", type=["jpg","png","pdf"])
    if u and st.button("Extrair"):
        with st.spinner("Processando..."):
            res = call_ai("Transcreva fielmente.", file_bytes=u.getvalue(), type="vision")
            st.text_area("Texto:", res, height=400)

# --- 6. TRANSCRIÇÃO ---
elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição")
    
    tab_upload, tab_mic = st.tabs(["📂 Upload de Arquivo", "🎤 Microfone"])
    
    with tab_upload:
        st.info("Ideal para músicas, atas gravadas ou reuniões longas.")
        audio_upload = st.file_uploader("Solte o áudio aqui (mp3, wav, m4a)", type=["mp3", "wav", "m4a", "ogg"])
        if audio_upload:
            if st.button("Transcrever Arquivo"):
                with st.spinner("Processando áudio..."):
                    res = call_ai("", file_bytes=audio_upload.getvalue(), type="audio")
                    st.success("Transcrição Concluída:")
                    st.text_area("Resultado:", res, height=300)

    with tab_mic:
        st.info("Ideal para ditados rápidos.")
        if hasattr(st, "audio_input"):
            audio_mic = st.audio_input("Clique para gravar")
            if audio_mic:
                with st.spinner("Transcrevendo..."):
                    res = call_ai("", file_bytes=audio_mic.getvalue(), type="audio")
                    st.success("Transcrição Concluída:")
                    st.text_area("Resultado (Mic):", res, height=300)
        else:
            st.warning("⚠️ Seu sistema não suporta gravação direta. Use a aba Upload.")
