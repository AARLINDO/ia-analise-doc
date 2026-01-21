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
    page_title="Carmélio AI | Suíte Jurídica Pro",
    page_icon="logo.jpg.png", # <--- Sua logo na aba do navegador
    layout="wide"
)

# CSS Dark Mode Premium & Gamificação
st.markdown("""
<style>
    /* GERAL */
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    
    /* CARDS */
    .question-card { background-color: #1F2430; padding: 20px; border-radius: 12px; border-left: 5px solid #3B82F6; margin-bottom: 15px; }
    .flashcard { background: linear-gradient(135deg, #1F2430 0%, #282C34 100%); padding: 24px; border-radius: 12px; border: 1px solid #3B82F6; text-align: center; }
    .xp-badge { background-color: #FFD700; color: #000; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 12px; }
    
    /* INPUTS & BUTTONS */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #161922; border: 1px solid #2B2F3B; color: #E0E7FF; border-radius: 8px;
    }
    .stButton>button {
        width: 100%; border-radius: 8px; height: 45px; font-weight: 600; border: none;
        background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%);
        color: white; transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4); color: white;}
    
    /* TYPOGRAPHY */
    h1, h2, h3 { color: #F3F4F6; font-family: 'Inter', sans-serif; }
    p, label, .stMarkdown { color: #9CA3AF; }
    
    /* PROFILE CARD */
    .profile-box { text-align: center; margin-bottom: 20px; color: #E0E7FF; }
    .profile-name { font-weight: bold; font-size: 18px; margin-top: 5px; color: #FFFFFF; }
    .profile-role { font-size: 12px; color: #3B82F6; text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. SISTEMA DE GAMIFICAÇÃO & ESTADO
# =============================================================================
if "user_xp" not in st.session_state: st.session_state.user_xp = 0
if "user_level" not in st.session_state: st.session_state.user_level = 1

def add_xp(amount):
    st.session_state.user_xp += amount
    # Lógica simples de nível: a cada 100xp sobe de nível
    new_level = (st.session_state.user_xp // 100) + 1
    if new_level > st.session_state.user_level:
        st.toast(f"🎉 PARABÉNS! Você subiu para o Nível {new_level}!", icon="🆙")
        st.session_state.user_level = new_level
    else:
        st.toast(f"+{amount} XP ganho!", icon="⭐")

# =============================================================================
# 3. BACKEND ROBUSTO (API GROQ REAL)
# =============================================================================
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return None, "⚠️ Configure a GROQ_API_KEY nos Secrets."
    return Groq(api_key=api_key), None

def criar_docx(texto, titulo="Documento Carmélio AI"):
    try:
        doc = Document()
        doc.add_heading(titulo, 0)
        for p in str(texto).split('\n'):
            if p.strip(): doc.add_paragraph(p)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        return None

def processar_ia(prompt, file_bytes=None, task_type="text", system_instruction="Você é um assistente útil.", model_override=None, temperature=0.3):
    client, erro = get_groq_client()
    if erro: return f"Erro de Configuração: {erro}"
    
    try:
        # Roteamento de Modelos
        if task_type == "vision":
            model = "llama-3.2-11b-vision-preview"
        elif task_type == "audio":
            model = "whisper-large-v3"
        else:
            # Texto: Usa o Versatile (70b) para coisas complexas, ou o override
            model = model_override if model_override else "llama-3.3-70b-versatile"

        # Chamada VISÃO
        if task_type == "vision" and file_bytes:
            b64 = base64.b64encode(file_bytes).decode('utf-8')
            return client.chat.completions.create(
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt},{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
                model=model, temperature=0.1
            ).choices[0].message.content

        # Chamada ÁUDIO
        elif task_type == "audio" and file_bytes:
            import tempfile
            suffix = ".mp3"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes); tmp_path = tmp.name
            with open(tmp_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), file.read()),
                    model=model, response_format="text", language="pt"
                )
            os.unlink(tmp_path)
            return transcription

        # Chamada TEXTO Padrão
        else:
            return client.chat.completions.create(
                messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}],
                model=model, temperature=temperature
            ).choices[0].message.content
            
    except Exception as e:
        return f"❌ Erro na IA: {str(e)}"

# Validador de JSON para Questões
def validate_json_response(response_text):
    try:
        # Tenta encontrar o JSON dentro da resposta (caso a IA fale antes)
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
            # Verifica campos obrigatórios
            required = ["enunciado", "alternativas", "gabarito", "comentario"]
            if all(key in data for key in required):
                return data
    except:
        pass
    return None

# =============================================================================
# 4. BARRA LATERAL (LOGO, LINKS E NAVEGAÇÃO)
# =============================================================================
with st.sidebar:
    # 1. LOGO E IDENTIDADE
    try: 
        st.image("logo.jpg.png", use_container_width=True)
    except: 
        st.warning("⚠️ Logo não encontrada.")

    st.markdown("""
    <div class="profile-box">
        <small>Desenvolvido por</small><br>
        <div class="profile-name">Arthur Carmélio</div>
        <div class="profile-role">Especialista Notarial & Dev</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. GAMIFICAÇÃO
    c_lvl, c_xp = st.columns(2)
    c_lvl.metric("Nível", st.session_state.user_level)
    c_xp.metric("XP", st.session_state.user_xp)
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))

    st.markdown("---")
    
    # 3. MENU
    menu_opcao = st.radio("Menu Principal:", 
        ["🎓 Área do Estudante", "💬 Mentor Jurídico", "📄 Redação de Contratos", "🏢 Cartório Digital (OCR)", "🎙️ Transcrição", "⭐ Feedback", "👤 Sobre"], 
        label_visibility="collapsed"
    )
    
    # 4. FERRAMENTA DE FOCO
    with st.expander("🍅 Pomodoro Timer"):
        tempo = st.slider("Minutos", 15, 60, 25)
        if st.button("Iniciar Foco"):
            st.toast(f"Foco de {tempo} minutos iniciado!")

    st.markdown("---")
    
    # 5. LINKS SOCIAIS (WHATSAPP E LINKEDIN)
    col_link, col_zap = st.columns(2)
    with col_link:
        st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")
    with col_zap:
        st.markdown("[![WhatsApp](https://img.shields.io/badge/Suporte-Zap-green?logo=whatsapp)](https://wa.me/5548920039720?text=Suporte%20Carmelio%20AI)")

# =============================================================================
# 5. MÓDULOS DO SISTEMA
# =============================================================================

# --- MÓDULO 1: ESTUDANTE PRO ---
if menu_opcao == "🎓 Área do Estudante":
    st.title("🎓 Área do Estudante Pro")
    tab_questoes, tab_edital, tab_flash, tab_crono = st.tabs(["📝 Banco Infinito", "🎯 Mestre dos Editais", "⚡ Flashcards", "📅 Cronograma"])

    # 1.1 BANCO DE QUESTÕES (JSON VALIDADO)
    with tab_questoes:
        st.markdown("### 🔎 Gerador de Questões Inéditas")
        c1, c2, c3, c4 = st.columns(4)
        disc = c1.selectbox("Disciplina", ["Constitucional", "Administrativo", "Penal", "Civil", "Proc. Penal", "Notarial", "Português", "Informática"])
        banca = c2.selectbox("Estilo Banca", ["FGV", "Cebraspe", "Vunesp", "FCC"])
        assunto = c3.text_input("Assunto", placeholder="Ex: Atos Administrativos")
        cargo = c4.text_input("Cargo", placeholder="Ex: Escrevente")

        if st.button("Gerar Questão"):
            with st.spinner("Elaborando questão..."):
                prompt = f"""Crie 1 questão inédita difícil. Disciplina: {disc}. Assunto: {assunto}. Banca: {banca}. Cargo: {cargo}.
                Responda EXCLUSIVAMENTE em formato JSON com chaves: 'enunciado', 'alternativas' (objeto com A,B,C,D,E), 'gabarito' (apenas a letra), 'comentario'."""
                res = processar_ia(prompt, task_type="text", temperature=0.2)
                
                data = validate_json_response(res)
                if data:
                    st.session_state.q_atual = data
                    st.session_state.ver_resp = False
                    add_xp(10) # Ganha XP
                else:
                    st.error("Erro na geração. Tente novamente.")
        
        if 'q_atual' in st.session_state:
            q = st.session_state.q_atual
            st.markdown(f"<div class='question-card'><h4>{disc} | {banca}</h4><p>{q['enunciado']}</p></div>", unsafe_allow_html=True)
            st.write("Alternativas:")
            for k, v in q['alternativas'].items():
                st.write(f"**{k})** {v}")
            
            if st.button("👁️ Ver Gabarito"):
                st.session_state.ver_resp = True
            
            if st.session_state.get('ver_resp'):
                st.success(f"Gabarito: {q['gabarito']}")
                st.info(f"Comentário: {q['comentario']}")

    # 1.2 MESTRE DOS EDITAIS (RECUPERADO)
    with tab_edital:
        st.markdown("### 🎯 Verticalizador de Editais")
        texto_edital = st.text_area("Cole o Edital aqui:", height=150)
        c_v, c_s = st.columns(2)
        if c_v.button("📊 Verticalizar Edital"):
            if texto_edital:
                with st.spinner("Processando..."):
                    p = f"Crie uma tabela de controle de estudos verticalizada baseada neste edital: {texto_edital}"
                    r = processar_ia(p)
                    st.markdown(r)
                    add_xp(20)
                    if criar_docx(r): st.download_button("💾 Baixar", criar_docx(r), "Edital.docx")
        
        if c_s.button("📝 Criar Simulado do Edital"):
            if texto_edital:
                with st.spinner("Criando simulado..."):
                    p = f"Crie 3 questões baseadas nos tópicos deste edital: {texto_edital}"
                    r = processar_ia(p)
                    st.write(r)
                    add_xp(30)

    # 1.3 FLASHCARDS COM ANKI
    with tab_flash:
        st.markdown("### ⚡ Flashcards & Exportação Anki")
        tema = st.text_input("Tema do Flashcard")
        if "cards" not in st.session_state: st.session_state.cards = []

        if st.button("Criar Flashcard"):
            r = processar_ia(f"Crie um flashcard sobre {tema}. Retorne: PERGUNTA --- RESPOSTA")
            if "---" in r:
                f, b = r.split("---")
                st.session_state.cards.append((f, b))
                st.success("Criado!")
                add_xp(5)
            else:
                st.error("Erro formato.")
        
        if st.session_state.cards:
            st.write(f"Você tem {len(st.session_state.cards)} cartas.")
            # Exportação CSV simples para Anki
            csv = "front,back\n" + "\n".join([f"{f.strip()},{b.strip()}" for f,b in st.session_state.cards])
            st.download_button("💾 Baixar CSV para Anki", csv, "anki_deck.csv")

    # 1.4 CRONOGRAMA
    with tab_crono:
        st.markdown("### 📅 Cronograma Inteligente")
        h = st.slider("Horas/Dia", 1, 8, 4)
        obj = st.text_input("Objetivo", "Concurso Cartório")
        if st.button("Gerar Plano"):
            r = processar_ia(f"Crie um cronograma de estudos para {obj} com {h}h/dia.")
            st.markdown(r)
            add_xp(15)

# --- MÓDULO 2: MENTOR JURÍDICO ---
elif menu_opcao == "💬 Mentor Jurídico":
    st.title("💬 Mentor Jurídico")
    perfil = st.selectbox("Perfil", ["Professor", "Doutrinador", "Jurisprudencial"])
    
    if "chat" not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat:
        st.chat_message(m["role"]).write(m["content"])
    
    if p := st.chat_input("Dúvida jurídica..."):
        st.session_state.chat.append({"role": "user", "content": p})
        st.chat_message("user").write(p)
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                sys = f"Aja como um {perfil}. Cite fontes."
                r = processar_ia(p, system_instruction=sys)
                st.write(r)
                st.session_state.chat.append({"role": "assistant", "content": r})

# --- MÓDULO 3: CONTRATOS ---
elif menu_opcao == "📄 Redação de Contratos":
    st.title("📄 Redação de Contratos")
    tipo = st.selectbox("Documento", ["Contrato", "Petição", "Procuração"])
    c1, c2 = st.columns(2)
    pa = c1.text_input("Parte A")
    pb = c2.text_input("Parte B")
    detalhes = st.text_area("Detalhes")
    
    if st.button("Redigir"):
        if detalhes:
            prompt = f"Redija um {tipo}. Parte A: {pa}. Parte B: {pb}. Detalhes: {detalhes}. Linguagem formal."
            r = processar_ia(prompt, model_override="llama-3.3-70b-versatile")
            st.text_area("Minuta", r, height=400)
            if criar_docx(r): st.download_button("💾 Baixar DOCX", criar_docx(r), f"{tipo}.docx")

# --- MÓDULO 4: CARTÓRIO OCR (VISION REAL) ---
elif menu_opcao == "🏢 Cartório Digital (OCR)":
    st.title("🏢 Cartório Digital (Vision AI)")
    st.info("Usa Visão Computacional para transcrever certidões antigas.")
    
    u = st.file_uploader("Imagem da Certidão", type=["jpg", "png"])
    if u and st.button("📝 Transcrever Inteiro Teor"):
        with st.spinner("Lendo documento manuscrito..."):
            prompt = "Transcreva este documento fielmente. Formate como Certidão de Inteiro Teor. Indique [Selo] e [Assinatura]."
            r = processar_ia(prompt, file_bytes=u.getvalue(), task_type="vision")
            st.text_area("Transcrição", r, height=400)
            if criar_docx(r): st.download_button("💾 Baixar DOCX", criar_docx(r), "Inteiro_Teor.docx")

# --- MÓDULO 5: TRANSCRIÇÃO (MIC + UPLOAD) ---
elif menu_opcao == "🎙️ Transcrição":
    st.title("🎙️ Transcrição de Áudio")
    tab_mic, tab_up = st.tabs(["🎤 Gravar", "📂 Upload"])
    
    with tab_mic:
        audio = st.audio_input("Gravar")
        if audio and st.button("Transcrever Gravação"):
            with st.spinner("Ouvindo..."):
                r = processar_ia("", file_bytes=audio.getvalue(), task_type="audio")
                st.write(r)
                if criar_docx(r): st.download_button("Download", criar_docx(r), "Audio.docx")
    
    with tab_up:
        upl = st.file_uploader("Arquivo MP3/WAV", type=["mp3", "wav", "m4a"])
        if upl and st.button("Transcrever Arquivo"):
            with st.spinner("Processando..."):
                r = processar_ia("", file_bytes=upl.getvalue(), task_type="audio")
                st.write(r)

# --- MÓDULO 6: FEEDBACK ---
elif menu_opcao == "⭐ Feedback":
    st.title("⭐ Avalie o Carmélio AI")
    with st.form("feed"):
        nota = st.slider("Nota", 1, 5, 5)
        msg = st.text_area("Sugestão")
        if st.form_submit_button("Enviar"):
            st.balloons()
            st.success("Obrigado pelo feedback!")
            add_xp(50)

# --- SOBRE ---
else:
    st.title("👤 Sobre o Autor")
    c1, c2 = st.columns([1,2])
    with c1: 
        try: st.image("logo.jpg.png", width=200)
        except: st.write("⚖️")
    with c2:
        st.markdown("""
        ### Arthur Carmélio
        **Desenvolvedor & Especialista Jurídico**
        
        O **Carmélio AI** nasceu da necessidade de unir a tradição do Direito com a velocidade da Tecnologia.
        
        * 🎓 Bacharel em Direito
        * 📜 Especialista Notarial
        * 💻 Desenvolvedor Python
        
        ---
        **Contato:**
        * [LinkedIn](https://www.linkedin.com/in/arthurcarmelio/)
        * [WhatsApp](https://wa.me/5548920039720)
        """)
