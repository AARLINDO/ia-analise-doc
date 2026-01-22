import streamlit as st
from groq import Groq
from docx import Document
from io import BytesIO
from datetime import datetime, timedelta
import json
import base64
import time
import re
import os

# =============================================================================
# 1. CONFIGURAÇÃO E DESIGN
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Suíte Jurídica",
    page_icon="logo.jpg.png",
    layout="wide"
)

# Tentativa de importação segura
try: import pdfplumber
except ImportError: pdfplumber = None
try: import docx as docx_reader
except ImportError: docx_reader = None
try: from PIL import Image, ImageFilter, ImageOps
except ImportError: Image = None

st.markdown("""
<style>
    /* GERAL */
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    
    /* CAIXAS DE EXPLICAÇÃO */
    .stAlert { background-color: #1F2937; color: #E5E7EB; border: 1px solid #374151; }
    
    /* POMODORO TIMER */
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@700&display=swap');
    .timer-container {
        background-color: #1F2430; border-radius: 20px; padding: 30px;
        text-align: center; border: 1px solid #2B2F3B; margin: 20px auto;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 600px;
    }
    .timer-display {
        font-family: 'Roboto Mono', monospace; font-size: 130px; font-weight: 700;
        color: #FFFFFF; line-height: 1; margin: 10px 0;
        text-shadow: 0 0 25px rgba(59, 130, 246, 0.5);
    }
    .timer-label {
        font-family: 'Inter', sans-serif; font-size: 18px; text-transform: uppercase;
        letter-spacing: 4px; color: #60A5FA; margin-bottom: 10px; font-weight: 600;
    }

    /* BOTÕES */
    .stButton>button {
        border-radius: 10px; font-weight: 600; height: 50px; border: none; transition: 0.2s;
    }
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white; font-size: 18px; box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.4);
    }
    div[data-testid="stHorizontalBlock"] button[kind="primary"]:hover {
        transform: scale(1.02);
    }

    /* PERFIL */
    .profile-box { text-align: center; margin-bottom: 30px; margin-top: 10px; }
    .profile-dev { font-size: 12px; color: #9CA3AF; margin-bottom: 2px; }
    .profile-name { font-weight: 700; font-size: 20px; color: #FFFFFF; }
    
    /* CARDS */
    .question-card { background-color: #1F2430; padding: 25px; border-radius: 12px; border-left: 4px solid #3B82F6; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. GESTÃO DE ESTADO
# =============================================================================
DEFAULTS = {
    "user_xp": 0, "user_level": 1,
    "edital_text": "", "edital_topics": [],
    "generated_questions": [], "logs": [], "cards": [],
    "lgpd_ack": False, "last_heavy_call": 0.0,
    # Pomodoro
    "pomo_state": "STOPPED", "pomo_mode": "Foco", 
    "pomo_duration": 25 * 60, "pomo_end_time": None,
    "pomo_auto_start": False
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

RATE_LIMIT_SECONDS = 3

def check_rate_limit():
    now = time.time()
    if now - st.session_state.last_heavy_call < RATE_LIMIT_SECONDS:
        return True
    return False

def mark_call():
    st.session_state.last_heavy_call = time.time()

def add_xp(amount):
    st.session_state.user_xp += amount
    new_level = (st.session_state.user_xp // 100) + 1
    if new_level > st.session_state.user_level:
        st.toast(f"🎉 Nível {new_level} alcançado!", icon="🆙")
        st.session_state.user_level = new_level
    else:
        st.toast(f"+{amount} XP", icon="⭐")

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

def create_docx(text, title="Documento Carmélio AI"):
    try:
        doc = Document()
        doc.add_heading(title, 0)
        for p in str(text).split('\n'):
            if p.strip(): doc.add_paragraph(p)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except: return None

# =============================================================================
# 3. MOTOR DE IA (GROQ)
# =============================================================================
def get_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return None
    return Groq(api_key=api_key)

def call_ai(prompt, file_bytes=None, type="text", system="Você é um assistente útil.", temp=0.3):
    if check_rate_limit(): return None
    client = get_client()
    if not client: return "⚠️ Configure a GROQ_API_KEY."
    
    mark_call()
    try:
        if type == "text":
            r = client.chat.completions.create(
                messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
                model="llama-3.3-70b-versatile", temperature=temp
            )
            return r.choices[0].message.content
            
        elif type == "vision" and file_bytes:
            b64 = base64.b64encode(file_bytes).decode('utf-8')
            r = client.chat.completions.create(
                messages=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}],
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
            
    except Exception as e:
        return f"Erro na IA: {e}"

# =============================================================================
# 4. SIDEBAR
# =============================================================================
with st.sidebar:
    # LOGO
    try: st.image("logo.jpg.png", use_container_width=True)
    except: pass
    
    # PERFIL SIMPLIFICADO
    st.markdown("""
    <div class="profile-box">
        <div class="profile-dev">Desenvolvido por</div>
        <div class="profile-name">Arthur Carmélio</div>
    </div>
    """, unsafe_allow_html=True)

    # GAMIFICAÇÃO DISCRETA
    c1, c2 = st.columns(2)
    c1.metric("Nível", st.session_state.user_level)
    c2.metric("XP", st.session_state.user_xp)
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))
    
    st.markdown("---")
    
    # NAVEGAÇÃO CLARA
    menu = st.radio("Selecione a Ferramenta:", 
        ["🎯 Mestre dos Editais", "🍅 Sala de Foco", "💬 Mentor Jurídico", "📄 Redação & Peças", "⚡ Flashcards", "📅 Cronograma", "🏢 Cartório OCR", "🎙️ Transcrição"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720)")

# LGPD Bloqueio
if not st.session_state.lgpd_ack:
    with st.expander("🔐 Acesso Seguro ao Sistema", expanded=True):
        st.write("Ao utilizar esta ferramenta, você concorda com o processamento de dados via Inteligência Artificial para fins educacionais e profissionais.")
        if st.button("Concordo e Entrar"):
            st.session_state.lgpd_ack = True
            st.rerun()
    st.stop()

# =============================================================================
# 5. MÓDULOS (COM EXPLICAÇÕES DIDÁTICAS)
# =============================================================================

# --- MESTRE DOS EDITAIS (O CORAÇÃO DO SISTEMA) ---
if menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais & Questões")
    
    # Explicação Didática
    st.info("""
    **Para que serve:** Esta é a sua central de estratégia. Aqui você transforma um edital PDF gigante em um plano de ação.
    
    1. **Suba seu Edital:** A IA vai ler o arquivo e entender o que cai na prova.
    2. **Verticalize:** Crie uma lista organizada dos tópicos.
    3. **Treine:** Gere questões inéditas baseadas *exatamente* no seu edital.
    """)

    # Área de Upload
    with st.container():
        c_up, c_btn = st.columns([2, 1])
        with c_up:
            file = st.file_uploader("Carregue seu Edital (PDF ou DOCX)", type=["pdf", "docx"])
        with c_btn:
            if st.session_state.edital_text:
                st.success("✅ Edital Ativo!")
                if st.button("❌ Trocar Edital"):
                    st.session_state.edital_text = ""
                    st.rerun()

    # Lógica de Leitura
    if file and not st.session_state.edital_text:
        with st.spinner("🔍 A IA está lendo cada linha do seu edital..."):
            raw = "Conteúdo..."
            if file.type == "application/pdf" and pdfplumber:
                with pdfplumber.open(BytesIO(file.getvalue())) as pdf: raw = "".join([p.extract_text() or "" for p in pdf.pages])
            elif "word" in file.type and docx_reader:
                doc = docx_reader.Document(BytesIO(file.getvalue()))
                raw = "\n".join([p.text for p in doc.paragraphs])
            
            st.session_state.edital_text = raw
            st.rerun()

    # Área de Ação
    st.markdown("---")
    st.subheader("📚 O que você quer fazer agora?")
    
    tab_treino, tab_vert = st.tabs(["📝 Criar Questões de Prova", "📊 Verticalizar Conteúdo"])
    
    with tab_treino:
        st.write("A IA criará questões focadas no seu objetivo.")
        
        # Se tem edital, foca nele. Se não, modo livre.
        modo_treino = "🎯 Focado no Edital" if st.session_state.edital_text else "🎲 Modo Livre (Sem Edital)"
        st.caption(f"Modo Atual: **{modo_treino}**")
        
        c1, c2, c3 = st.columns(3)
        disc = c1.selectbox("Disciplina", ["Direito Constitucional", "Administrativo", "Penal", "Civil", "Proc. Penal", "Notarial"])
        banca = c2.selectbox("Banca", ["FGV", "Cebraspe", "Vunesp", "FCC"])
        assunto = c3.text_input("Assunto Específico", "Atos Administrativos")

        if st.button("🚀 Gerar Questão Inédita", type="primary", use_container_width=True):
            with st.spinner("Elaborando questão com base nos parâmetros..."):
                ctx = st.session_state.edital_text[:4000] if st.session_state.edital_text else ""
                prompt = (
                    f"Crie uma questão de concurso inédita. Banca: {banca}. Disciplina: {disc}. Assunto: {assunto}. "
                    f"Contexto do Edital: {ctx}. "
                    "Retorne JSON dentro de <json>...</json> com: enunciado, alternativas (A-E), gabarito, comentario."
                )
                res = call_ai(prompt, temp=0.4)
                data = extract_json_safe(res)
                
                if data:
                    st.session_state.q_atual = data
                    st.session_state.ver_resp = False
                    add_xp(10)
                else:
                    st.error("A IA não conseguiu gerar. Tente mudar o assunto.")

        # Exibição da Questão
        if 'q_atual' in st.session_state:
            q = st.session_state.q_atual
            st.markdown(f"<div class='question-card'><h5>{banca} | {disc}</h5><p style='font-size:18px; color:white;'>{q.get('enunciado')}</p></div>", unsafe_allow_html=True)
            for k, v in q.get('alternativas', {}).items():
                st.write(f"**{k})** {v}")
            
            if st.button("👁️ Ver Gabarito"):
                st.session_state.ver_resp = True
            
            if st.session_state.get('ver_resp'):
                st.success(f"Gabarito: {q.get('gabarito')}")
                st.info(f"📝 **Comentário:** {q.get('comentario')}")

    with tab_vert:
        if st.button("📑 Gerar Edital Verticalizado"):
            if not st.session_state.edital_text:
                st.warning("Primeiro suba um edital no topo da página.")
            else:
                with st.spinner("Organizando tópicos..."):
                    res = call_ai(f"Faça uma lista verticalizada dos tópicos deste edital: {st.session_state.edital_text[:3000]}", temp=0.1)
                    st.markdown(res)
                    add_xp(20)

# --- SALA DE FOCO (POMODORO) ---
elif menu == "🍅 Sala de Foco":
    st.title("🍅 Sala de Foco & Produtividade")
    
    st.info("""
    **Para que serve:** O método Pomodoro divide seu tempo em blocos de foco intenso e descanso.
    Isso mantém seu cérebro descansado e aumenta a retenção do conteúdo estudado.
    
    * **Foco (25m):** Estude sem interrupções.
    * **Descanso (5m):** Levante, beba água, estique as pernas.
    """)
    
    # 1. Seletor de Modo
    c_m1, c_m2, c_m3 = st.columns(3)
    def set_pomo(mode, min):
        st.session_state.pomo_mode = mode
        st.session_state.pomo_duration = min * 60
        st.session_state.pomo_state = "STOPPED"
        st.session_state.pomo_end_time = None
        st.rerun()

    if c_m1.button("🧠 FOCO (25m)", use_container_width=True): set_pomo("Foco", 25)
    if c_m2.button("☕ CURTO (5m)", use_container_width=True): set_pomo("Descanso", 5)
    if c_m3.button("🧘 LONGO (15m)", use_container_width=True): set_pomo("Longo", 15)

    # 2. Lógica do Timer
    remaining = st.session_state.pomo_duration
    if st.session_state.pomo_state == "RUNNING":
        now = time.time()
        if now >= st.session_state.pomo_end_time:
            st.session_state.pomo_state = "STOPPED"
            st.balloons()
            st.markdown("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", unsafe_allow_html=True)
            add_xp(50)
            
            # Automação
            if st.session_state.pomo_auto_start:
                next_mode = "Descanso" if st.session_state.pomo_mode == "Foco" else "Foco"
                next_min = 5 if next_mode == "Descanso" else 25
                st.session_state.pomo_mode = next_mode
                st.session_state.pomo_duration = next_min * 60
                st.session_state.pomo_end_time = time.time() + (next_min * 60)
                st.session_state.pomo_state = "RUNNING"
                time.sleep(2)
                st.rerun()
            else:
                remaining = 0
        else:
            remaining = int(st.session_state.pomo_end_time - now)
            time.sleep(1)
            st.rerun()

    # 3. Visual
    mins, secs = divmod(remaining, 60)
    time_str = f"{mins:02d}:{secs:02d}"
    
    st.markdown(f"""
    <div class="timer-container">
        <div class="timer-label">{st.session_state.pomo_mode}</div>
        <div class="timer-display">{time_str}</div>
    </div>
    """, unsafe_allow_html=True)

    # 4. Controles
    c_play, c_pause, c_reset = st.columns(3)
    if c_play.button("COMEÇAR", type="primary", use_container_width=True): 
        if st.session_state.pomo_state != "RUNNING":
            st.session_state.pomo_state = "RUNNING"
            st.session_state.pomo_end_time = time.time() + remaining
            st.rerun()
    if c_pause.button("PAUSAR", use_container_width=True): 
        if st.session_state.pomo_state == "RUNNING":
            st.session_state.pomo_state = "PAUSED"
            st.session_state.pomo_duration = remaining
            st.rerun()
    if c_reset.button("ZERAR", use_container_width=True): 
        st.session_state.pomo_state = "STOPPED"
        defaults = {"Foco": 25, "Descanso": 5, "Longo": 15}
        st.session_state.pomo_duration = defaults.get(st.session_state.pomo_mode, 25) * 60
        st.rerun()

    st.session_state.pomo_auto_start = st.checkbox("🔄 Iniciar ciclos automaticamente?", value=st.session_state.pomo_auto_start)

    with st.expander("🎵 Rádio Lofi (Música de Fundo)", expanded=False):
        st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")

# --- MENTOR JURÍDICO ---
elif menu == "💬 Mentor Jurídico":
    st.title("💬 Mentor Jurídico 24h")
    st.info("""
    **Para que serve:** Tire dúvidas sobre qualquer matéria jurídica. A IA atua como um professor especialista.
    **Exemplo:** "Qual a diferença entre Dolo Eventual e Culpa Consciente?" ou "Resuma o Art. 5º da CF."
    """)
    
    if p:=st.chat_input("Digite sua dúvida jurídica aqui..."):
        with st.chat_message("user"): st.write(p)
        with st.chat_message("assistant"):
            with st.spinner("Consultando jurisprudência e doutrina..."):
                res = call_ai(p, system="Você é um professor de direito didático e preciso. Cite leis e autores.")
                st.write(res)
                add_xp(5)

# --- REDAÇÃO ---
elif menu == "📄 Redação & Peças":
    st.title("📄 Redação Jurídica Inteligente")
    st.info("""
    **Para que serve:** Crie minutas de contratos, petições ou procurações em segundos.
    Apenas descreva o caso e a IA montará a estrutura formal completa para você revisar.
    """)
    
    tipo = st.selectbox("O que vamos redigir?", ["Contrato de Honorários", "Petição Inicial", "Contestação", "Procuração Ad Judicia", "Habeas Corpus"])
    det = st.text_area("Descreva os detalhes (Partes, Objeto, Fatos):", height=150)
    
    if st.button("✍️ Escrever Minuta"):
        with st.spinner("Redigindo documento com técnica jurídica..."):
            res = call_ai(f"Redija um(a) {tipo} completo. Detalhes: {det}. Use linguagem jurídica formal e cite artigos.", temp=0.2)
            st.text_area("Minuta Gerada:", res, height=400)
            add_xp(20)

# --- FLASHCARDS ---
elif menu == "⚡ Flashcards":
    st.title("⚡ Flashcards (Repetição Espaçada)")
    st.info("""
    **Para que serve:** A melhor técnica para memorizar prazos e conceitos.
    Crie cartões com Pergunta (Frente) e Resposta (Verso) e revise-os periodicamente.
    """)
    
    tema = st.text_input("Sobre o que você quer criar um card? (Ex: Prazos Penais)")
    if st.button("Criar Card com IA"):
        res = call_ai(f"Crie um flashcard difícil sobre {tema}. Retorne JSON <json>{{'front':'PERGUNTA', 'back':'RESPOSTA'}}</json>")
        data = extract_json_safe(res)
        if data:
            st.session_state.cards.append(data)
            st.success("Card Criado!")
            add_xp(5)
    
    if st.session_state.cards:
        st.write("---")
        for i, c in enumerate(st.session_state.cards):
            with st.expander(f"🃏 Card {i+1}: {c.get('front')}"):
                st.write(f"**Resposta:** {c.get('back')}")

# --- CRONOGRAMA ---
elif menu == "📅 Cronograma":
    st.title("📅 Planejador de Estudos")
    st.info("**Para que serve:** A IA organiza sua rotina. Diga quantas horas você tem e qual seu objetivo, e ela monta um quadro de horários.")
    
    h = st.slider("Horas disponíveis por dia:", 1, 10, 4)
    obj = st.text_input("Objetivo (Ex: OAB 40, Concurso TJSP):")
    
    if st.button("Gerar Cronograma"):
        with st.spinner("Montando estratégia..."):
            res = call_ai(f"Crie um cronograma de estudos semanal para {obj} com {h} horas líquidas diárias. Use o método de ciclo de estudos.", temp=0.4)
            st.write(res)
            add_xp(20)

# --- OCR ---
elif menu == "🏢 Cartório OCR":
    st.title("🏢 Cartório Digital (OCR)")
    st.info("**Para que serve:** Transforme fotos de certidões antigas ou documentos físicos em texto digital editável (Word/Bloco de Notas).")
    
    u = st.file_uploader("Envie a foto ou PDF", type=["jpg","png","pdf"])
    if u and st.button("Extrair Texto"):
        with st.spinner("Lendo documento..."):
            res = call_ai("Transcreva este documento fielmente, mantendo a formatação de Inteiro Teor.", file_bytes=u.getvalue(), type="vision")
            st.text_area("Texto Extraído:", res, height=400)
            add_xp(25)

# --- TRANSCRIÇÃO ---
elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição de Áudio")
    st.info("**Para que serve:** Grave uma aula, uma reunião ou um ditado e a IA transforma o áudio em texto escrito.")
    
    a = st.audio_input("Gravar Agora")
    if a and st.button("Transcrever"):
        with st.spinner("Ouvindo..."):
            res = call_ai("", file_bytes=a.getvalue(), type="audio")
            st.success("Transcrição Concluída:")
            st.write(res)
            add_xp(20)

# --- FEEDBACK ---
elif menu == "⭐ Feedback":
    st.title("⭐ Ajude a melhorar")
    st.write("Encontrou um erro ou tem uma ideia? Conte para o desenvolvedor.")
    st.text_area("Sua mensagem:")
    if st.button("Enviar"):
        st.balloons()
        st.success("Obrigado!")

# --- SOBRE ---
else:
    st.title("👤 Sobre")
    st.write("Carmélio AI - v17.0 Final Explained")
    st.write("Desenvolvido por Arthur Carmélio.")
