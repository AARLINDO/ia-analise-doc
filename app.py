import streamlit as st
from groq import Groq
from docx import Document
from io import BytesIO
import base64
import os

# ==============================================================================
# 1. CONFIGURAÇÃO E SEO
# ==============================================================================
st.set_page_config(
    page_title="Carmélio AI | Assistente Jurídico",
    page_icon="logo.jpg.png",  # <--- AQUI ESTÁ A MUDANÇA (Sua Logo na Aba!)
    layout="wide"
)

# CSS "Dark Mode Premium"
st.markdown("""
<style>
    /* GERAL */
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    
    /* INPUTS */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #161922; border: 1px solid #2B2F3B; color: #E0E7FF; border-radius: 8px;
    }
    
    /* BOTÕES */
    .stButton>button {
        width: 100%; border-radius: 8px; height: 45px; font-weight: 600; border: none;
        background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%);
        color: white; transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4); color: white;}
    
    /* TEXTOS */
    h1, h2, h3 { color: #F3F4F6; font-family: 'Inter', sans-serif; }
    p, label, .stMarkdown { color: #9CA3AF; }
    
    /* PERFIL LATERAL (SIMPLIFICADO) */
    .profile-card {
        background: #1F2430; padding: 15px; border-radius: 10px; border: 1px solid #2B2F3B;
        text-align: center; margin-bottom: 20px; margin-top: 10px;
    }
    .profile-label { color: #9CA3AF; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .profile-name { color: white; font-weight: bold; font-size: 18px; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DO SISTEMA (BACKEND)
# ==============================================================================
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return None, "⚠️ Configure a GROQ_API_KEY nos Secrets."
    return Groq(api_key=api_key), None

def criar_docx(texto):
    try:
        if not texto or "❌" in texto: return None
        doc = Document()
        doc.add_heading('Documento Carmélio AI', 0)
        for p in str(texto).replace('\x00', '').split('\n'):
            if p.strip(): doc.add_paragraph(p)
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
                tmp.write(file_bytes); tmp_path = tmp.name
            with open(tmp_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), file.read()),
                    model="whisper-large-v3", response_format="text", language="pt"
                )
            os.unlink(tmp_path)
            return transcription
        elif task_type == "vision" and file_bytes:
            b64 = base64.b64encode(file_bytes).decode('utf-8')
            return client.chat.completions.create(
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt},{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
                model="llama-3.2-11b-vision-preview", temperature=0.1
            ).choices[0].message.content
        else:
            return client.chat.completions.create(
                messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile", temperature=0.5
            ).choices[0].message.content
    except Exception as e: return f"❌ Erro na IA: {str(e)}"

# ==============================================================================
# 3. BARRA LATERAL (LIMPA E MODERNA)
# ==============================================================================
with st.sidebar:
    # --- LOGO ---
    try:
        st.image("logo.jpg.png", use_container_width=True)
    except:
        st.warning("⚠️ Logo não encontrada.")

    # --- CARD DE AUTORIA (SIMPLIFICADO) ---
    st.markdown("""
    <div class="profile-card">
        <div class="profile-label">Desenvolvido por</div>
        <div class="profile-name">Arthur Carmélio</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Menu Principal")
    menu_opcao = st.radio(
        "Navegação:",
        ["💬 Mentor Jurídico", "🎓 Área do Estudante", "📄 Redação de Contratos", "🏢 Cartório Digital", "🎙️ Transcrição", "👤 Sobre o Autor"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1: st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")
    with c2: st.markdown("[![WhatsApp](https://img.shields.io/badge/WhatsApp-Falar-green?logo=whatsapp)](https://wa.me/5548920039720)")

# ==============================================================================
# 4. ÁREA PRINCIPAL
# ==============================================================================

# --- MÓDULO 1: MENTOR JURÍDICO ---
if "Mentor" in menu_opcao:
    st.title("💬 Mentor Jurídico IA")
    st.caption("Tira-dúvidas jurídicas, análise de casos e jurisprudência.")
    
    c_conf, c_chat = st.columns([1, 3])
    with c_conf:
        st.markdown("#### Personalidade")
        perfil = st.selectbox("Modo:", ["Advogado Sênior", "Mentor Policial", "Tabelião"])
        sys = "Seja formal e técnico." if "Advogado" in perfil else "Foco em Penal e Concursos." if "Policial" in perfil else "Foco em Registros Públicos."
        if st.button("Limpar"): st.session_state.chat = []; st.rerun()

    with c_chat:
        if 'chat' not in st.session_state: st.session_state.chat = []
        for m in st.session_state.chat:
            st.chat_message(m['role'], avatar="⚖️" if m['role']=="assistant" else "👤").write(m['content'])
        
        if p:=st.chat_input("Digite sua dúvida..."):
            st.session_state.chat.append({"role":"user", "content":p})
            st.chat_message("user").write(p)
            with st.chat_message("assistant", avatar="⚖️"):
                with st.spinner("Pesquisando..."):
                    r = processar_ia(p, task_type="text", system_instruction=sys)
                    st.write(r)
                    st.session_state.chat.append({"role":"assistant", "content":r})
            if r:
                st.download_button("💾 Baixar Resposta", criar_docx(r), "Parecer.docx")

# --- MÓDULO 2: ÁREA DO ESTUDANTE ---
elif "Estudante" in menu_opcao:
    st.title("🎓 Área do Estudante & Concurseiro")
    st.caption("Ferramentas de Estudo Ativo para OAB e Concursos Públicos.")
    
    tab_flash, tab_quiz = st.tabs(["🗂️ Gerador de Flashcards", "📝 Quiz/Simulado"])
    
    with tab_flash:
        st.markdown("### Crie resumos rápidos para memorização")
        tema_flash = st.text_input("Qual o tema?", placeholder="Ex: Art. 5 da CF, Crimes contra a Vida, Usucapião...")
        qtd_flash = st.slider("Quantidade de Cartões:", 3, 10, 5)
        
        if st.button("Gerar Flashcards"):
            with st.spinner(f"Criando {qtd_flash} flashcards sobre {tema_flash}..."):
                prompt = f"Crie {qtd_flash} Flashcards de estudo sobre '{tema_flash}'. Formato: PERGUNTA (em negrito) e RESPOSTA (curta e direta). Use emojis."
                res_flash = processar_ia(prompt, task_type="text", system_instruction="Você é um professor focado em memorização.")
                st.markdown(res_flash)
                st.download_button("💾 Baixar Flashcards", criar_docx(res_flash), "Flashcards.docx")
                
    with tab_quiz:
        st.markdown("### Teste seus conhecimentos")
        tema_quiz = st.text_input("Matéria do Simulado:", placeholder="Ex: Direito Administrativo - Atos Administrativos")
        dificuldade = st.select_slider("Dificuldade:", ["Fácil", "Médio", "Difícil (FGV/Cebraspe)"])
        
        if st.button("Gerar Simulado"):
            with st.spinner("Elaborando questões..."):
                prompt = f"Crie um simulado com 3 questões de múltipla escolha sobre '{tema_quiz}'. Nível: {dificuldade}. No final, coloque o GABARITO COMENTADO."
                res_quiz = processar_ia(prompt, task_type="text", system_instruction="Você é um examinador de banca de concurso.")
                st.info("Responda mentalmente antes de ver o gabarito no final!")
                st.write(res_quiz)
                st.download_button("💾 Baixar Simulado", criar_docx(res_quiz), "Simulado.docx")

# --- MÓDULO 3: CONTRATOS ---
elif "Contratos" in menu_opcao:
    st.title("📄 Redação de Contratos")
    t = st.selectbox("Tipo:", ["Aluguel Residencial", "Comercial", "Compra e Venda", "Serviços"])
    c1, c2 = st.columns(2)
    a = c1.text_input("Contratante", placeholder="Nome, CPF...")
    b = c2.text_input("Contratado", placeholder="Nome, CPF...")
    val = c1.text_input("Valor", placeholder="R$...")
    obj = c2.text_input("Objeto", placeholder="Descrição...")
    if st.button("🚀 Gerar Minuta"):
        if a and val:
            with st.spinner("Redigindo..."):
                prompt = f"Atue como Tabelião. Redija um {t} completo (ABNT). LOCADOR: {a}, LOCATÁRIO: {b}, VALOR: {val}, OBJETO: {obj}. Inclua cláusulas de praxe, foro e multa."
                r = processar_ia(prompt, task_type="text")
                st.session_state['cont'] = r
    if 'cont' in st.session_state:
        st.write(st.session_state['cont'])
        st.download_button("💾 Baixar DOCX", criar_docx(st.session_state['cont']), "Contrato.docx")

# --- MÓDULO 4: CARTÓRIO ---
elif "Cartório" in menu_opcao:
    st.title("🏢 Cartório Digital (OCR)")
    u = st.file_uploader("Documento", type=["jpg","pdf"])
    if u and st.button("Extrair"):
        with st.spinner("Lendo..."):
            r = processar_ia("Transcreva este documento.", file_bytes=u.getvalue(), task_type="vision")
            st.text_area("Texto", r, height=400)
            st.download_button("💾 Baixar DOCX", criar_docx(r), "Doc.docx")

# --- MÓDULO 5: TRANSCRIÇÃO ---
elif "Transcrição" in menu_opcao:
    st.title("🎙️ Transcrição")
    u = st.audio_input("Gravar")
    if u and st.button("Transcrever"):
        with st.spinner("Ouvindo..."):
            r = processar_ia("", file_bytes=u.getvalue(), task_type="audio")
            st.write(r)
            st.download_button("💾 Baixar", criar_docx(r), "Audio.docx")

# --- MÓDULO 6: SOBRE O AUTOR ---
elif "Sobre" in menu_opcao:
    st.title("👤 Sobre o Autor")
    
    col_perfil, col_bio = st.columns([1, 2])
    
    with col_perfil:
        # Tenta mostrar a logo ou uma foto de perfil se você tiver
        try:
            st.image("logo.jpg.png", width=200)
        except:
            st.markdown("⚖️")
            
    with col_bio:
        st.markdown("""
        ### Arthur Carmélio
        **Desenvolvedor & Especialista Jurídico**
        
        Sou Bacharel em Direito e Especialista Notarial, apaixonado por unir a tradição jurídica com a inovação tecnológica. 
        
        Criei o **Carmélio AI** para resolver dores reais da profissão: a burocracia repetitiva, a necessidade de análise rápida de documentos e o estudo eficiente para concursos.
        
        **Formação & Expertise:**
        * 🎓 Bacharel em Direito
        * 📜 Especialista em Serviços Notariais e Registrais
        * 💻 Desenvolvedor Python com foco em IA (LLMs)
        
        ---
        **Contato:**
        * [LinkedIn](https://www.linkedin.com/in/arthurcarmelio/)
        * [WhatsApp](https://wa.me/5548920039720)
        """)
