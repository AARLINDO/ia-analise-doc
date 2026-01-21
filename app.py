import streamlit as st
from groq import Groq
from docx import Document
from io import BytesIO
import base64
import os
import datetime

# ==============================================================================
# 1. CONFIGURAÇÃO E DESIGN
# ==============================================================================
st.set_page_config(
    page_title="Carmélio AI | Suíte Jurídica",
    page_icon="logo.jpg.png",
    layout="wide"
)

# CSS "Dark Mode Premium" - Estilo QConcursos Dark
st.markdown("""
<style>
    /* GERAL */
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    
    /* CARDS DE QUESTÕES */
    .question-card {
        background-color: #1F2430; padding: 20px; border-radius: 10px; border: 1px solid #3B82F6;
        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
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
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES DO SISTEMA
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
# 3. BARRA LATERAL
# ==============================================================================
with st.sidebar:
    try: st.image("logo.jpg.png", use_container_width=True)
    except: st.warning("Logo não encontrada.")

    st.markdown("<div style='text-align: center; color: #9CA3AF; margin-bottom: 20px;'>Desenvolvido por<br><b style='color: white;'>Arthur Carmélio</b></div>", unsafe_allow_html=True)
    
    menu_opcao = st.radio("Menu:", ["🎓 Área do Estudante", "💬 Mentor Jurídico", "📄 Redação de Contratos", "🏢 Cartório Digital", "🎙️ Transcrição", "👤 Sobre"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://www.linkedin.com/in/arthurcarmelio/)")

# ==============================================================================
# 4. ÁREA PRINCIPAL
# ==============================================================================

# --- MÓDULO 1: ÁREA DO ESTUDANTE (UPGRADE TIPO QCONCURSOS) ---
if "Estudante" in menu_opcao:
    st.title("🎓 Área do Estudante Pro")
    st.caption("Treine com a inteligência do Gemini e a estrutura do QConcursos.")
    
    tab_questoes, tab_cronograma, tab_flash = st.tabs(["📝 Banco de Questões", "📅 Criar Cronograma", "⚡ Flashcards"])
    
    # --- SUB-ABA: BANCO DE QUESTÕES ---
    with tab_questoes:
        st.markdown("### 🔍 Filtros de Estudo")
        
        # Filtros estilo QConcursos
        c1, c2, c3, c4 = st.columns(4)
        disciplina = c1.selectbox("Disciplina", ["Direito Constitucional", "Direito Administrativo", "Direito Penal", "Processo Penal", "Direito Civil", "Notarial e Registral"])
        banca = c2.selectbox("Banca", ["FGV", "Cebraspe", "Vunesp", "FCC", "Indiferente"])
        cargo = c3.text_input("Cargo Foco", placeholder="Ex: Delegado, Escrevente")
        assunto = c4.text_input("Assunto Específico", placeholder="Ex: Atos Administrativos")
        
        if 'questao_atual' not in st.session_state: st.session_state.questao_atual = None
        if 'gabarito_atual' not in st.session_state: st.session_state.gabarito_atual = None
        
        if st.button("🔎 Gerar Nova Questão"):
            with st.spinner(f"A IA está criando uma questão inédita de {banca}..."):
                # Prompt avançado para criar JSON-like structure
                prompt = f"""
                Crie UMA questão de concurso inédita e difícil.
                Filtros: Disciplina: {disciplina}. Assunto: {assunto}. Banca estilo: {banca}. Cargo: {cargo}.
                
                FORMATO DE RESPOSTA OBRIGATÓRIO (Siga estritamente):
                ENUNCIADO: [Escreva o enunciado aqui]
                A) [Alternativa A]
                B) [Alternativa B]
                C) [Alternativa C]
                D) [Alternativa D]
                E) [Alternativa E]
                CORRETA: [Apenas a letra, ex: C]
                EXPLICAÇÃO: [Explique detalhadamente por que a correta é a correta e por que as outras estão erradas, citando artigos de lei].
                """
                res = processar_ia(prompt, task_type="text", system_instruction="Você é um examinador de banca de elite.")
                st.session_state.questao_atual = res
                st.session_state.mostrar_resposta = False # Esconde a resposta ao gerar nova
        
        # Exibição da Questão
        if st.session_state.questao_atual:
            # Separa o texto visualmente
            texto_completo = st.session_state.questao_atual
            
            # Tenta separar enunciado e alternativas da resposta (Truque simples de split)
            try:
                parte_visivel = texto_completo.split("CORRETA:")[0]
                parte_gabarito = "CORRETA:" + texto_completo.split("CORRETA:")[1]
            except:
                parte_visivel = texto_completo
                parte_gabarito = "Erro na formatação da IA. Tente gerar outra."

            st.markdown("---")
            st.markdown(f"""
            <div class="question-card">
                <h3>⚖️ Questão Inédita ({banca})</h3>
                <div style="font-size: 18px; white-space: pre-wrap;">{parte_visivel}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botões de Resposta
            col_botoes, col_ver = st.columns([3, 1])
            with col_botoes:
                st.caption("Marque sua resposta mentalmente e clique em conferir.")
            with col_ver:
                if st.button("👁️ Ver Gabarito Comentado"):
                    st.session_state.mostrar_resposta = True
            
            if st.session_state.get('mostrar_resposta'):
                st.success("✅ Gabarito e Comentários do Professor IA:")
                st.markdown(f"```text\n{parte_gabarito}\n```")
                st.info("💡 Dica: A IA explica citando a lei. Leia com atenção para fixar!")

    # --- SUB-ABA: CRONOGRAMA ---
    with tab_cronograma:
        st.markdown("### 📅 Planejador de Estudos Inteligente")
        c_horas = st.slider("Quantas horas você tem por dia?", 1, 8, 3)
        c_obj = st.text_input("Qual seu objetivo?", value="Passar na OAB/Concurso PCSC")
        c_dias = st.multiselect("Dias disponíveis:", ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"], default=["Seg", "Ter", "Qua", "Qui", "Sex"])
        
        if st.button("🗓️ Montar Meu Cronograma"):
            with st.spinner("A IA está organizando sua rotina..."):
                prompt = f"Crie uma tabela de estudos semanal para {c_obj}. Tenho {c_horas} horas por dia nos dias {c_dias}. Intercale Doutrina, Lei Seca e Questões. Seja realista."
                r = processar_ia(prompt, task_type="text")
                st.markdown(r)
                st.download_button("💾 Baixar Cronograma", criar_docx(r), "Cronograma.docx")

    # --- SUB-ABA: FLASHCARDS ---
    with tab_flash:
        st.markdown("### ⚡ Flashcards de Revisão")
        tema = st.text_input("Tema para revisar:", placeholder="Ex: Prazos Processuais Penais")
        if st.button("Gerar Flashcards"):
            with st.spinner("Criando..."):
                p = f"Crie 5 flashcards sobre {tema}. Formato: PERGUNTA (Frente) e RESPOSTA (Verso)."
                r = processar_ia(p, task_type="text")
                st.write(r)

# --- MÓDULO 2: MENTOR JURÍDICO ---
elif "Mentor" in menu_opcao:
    st.title("💬 Mentor Jurídico IA")
    modo = st.selectbox("Modo:", ["Professor Didático", "Advogado Técnico", "Mentor Policial"])
    
    if 'chat' not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat:
        st.chat_message(m['role'], avatar="⚖️" if m['role']=="assistant" else "👤").write(m['content'])
    
    if p:=st.chat_input("Dúvida jurídica..."):
        st.session_state.chat.append({"role":"user", "content":p})
        st.chat_message("user").write(p)
        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("Analisando..."):
                instrucao = "Seja didático." if "Professor" in modo else "Seja técnico e cite leis."
                r = processar_ia(p, task_type="text", system_instruction=instrucao)
                st.write(r)
                st.session_state.chat.append({"role":"assistant", "content":r})
        if r: st.download_button("💾 Baixar", criar_docx(r), "Resposta.docx")

# --- MÓDULO 3: CONTRATOS ---
elif "Contratos" in menu_opcao:
    st.title("📄 Redação de Contratos")
    t = st.selectbox("Tipo:", ["Aluguel Residencial", "Comercial", "Compra e Venda", "Serviços"])
    c1, c2 = st.columns(2)
    a = c1.text_input("Contratante")
    b = c2.text_input("Contratado")
    val = c1.text_input("Valor")
    obj = c2.text_input("Objeto")
    if st.button("🚀 Gerar Minuta"):
        if a and val:
            with st.spinner("Redigindo..."):
                prompt = f"Atue como Tabelião. Redija um {t} completo (ABNT). LOCADOR: {a}, LOCATÁRIO: {b}, VALOR: {val}, OBJETO: {obj}."
                r = processar_ia(prompt, task_type="text")
                st.session_state['cont'] = r
    if 'cont' in st.session_state:
        st.write(st.session_state['cont'])
        st.download_button("💾 Baixar DOCX", criar_docx(st.session_state['cont']), "Contrato.docx")

# --- MÓDULO 4: CARTÓRIO ---
elif "Cartório" in menu_opcao:
    st.title("🏢 Cartório Digital")
    u = st.file_uploader("Documento", type=["jpg","pdf"])
    if u and st.button("Extrair"):
        with st.spinner("Lendo..."):
            r = processar_ia("Transcreva.", file_bytes=u.getvalue(), task_type="vision")
            st.text_area("Texto", r, height=400)
            st.download_button("💾 Baixar", criar_docx(r), "Doc.docx")

# --- MÓDULO 5: TRANSCRIÇÃO ---
elif "Transcrição" in menu_opcao:
    st.title("🎙️ Transcrição")
    u = st.audio_input("Gravar")
    if u and st.button("Transcrever"):
        with st.spinner("Ouvindo..."):
            r = processar_ia("", file_bytes=u.getvalue(), task_type="audio")
            st.write(r)
            st.download_button("💾 Baixar", criar_docx(r), "Audio.docx")

# --- MÓDULO 6: SOBRE ---
elif "Sobre" in menu_opcao:
    st.title("👤 Sobre o Autor")
    c1, c2 = st.columns([1,2])
    with c1: 
        try: st.image("logo.jpg.png", width=200)
        except: st.write("⚖️")
    with c2:
        st.markdown("""
        ### Arthur Carmélio
        **Desenvolvedor & Especialista Jurídico**
        
        Ferramenta desenvolvida para revolucionar a rotina jurídica e de estudos.
        
        * 🎓 Bacharel em Direito
        * 📜 Especialista Notarial
        * 💻 Desenvolvedor Python
        """)
