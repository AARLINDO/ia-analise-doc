import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÃO E DESIGN "DASHBOARD JURIS"
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Suite", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    /* FUNDO GERAL */
    .stApp { background-color: #0E1117; }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] { background-color: #161a24; border-right: 1px solid #2b303b; }

    /* ESTILO DOS CARTÕES (TILES) */
    .dashboard-card {
        background-color: #1b1e26; border: 1px solid #333; border-radius: 10px;
        padding: 20px; text-align: center; transition: 0.3s; height: 200px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }
    
    /* BOTÕES DOURADOS (AÇÃO PRINCIPAL) */
    .stButton>button { 
        width: 100%; border-radius: 6px; height: 50px; font-weight: bold; border: none;
        background: linear-gradient(90deg, #967036, #C6A34F); color: #000;
        text-transform: uppercase; letter-spacing: 1px; transition: 0.3s;
    }
    .stButton>button:hover { background: linear-gradient(90deg, #C6A34F, #E5C365); color: #000; }
    
    /* LINK BUTTONS (WHATSAPP/LINKEDIN) - BOTÕES DE CONTATO */
    a[href^="https://wa.me"] {
        text-decoration: none; font-weight: bold; color: #25D366 !important;
        border: 1px solid #25D366; padding: 10px; border-radius: 5px; display: block; text-align: center; margin-top: 5px;
    }
    a[href^="https://www.linkedin.com"] {
        text-decoration: none; font-weight: bold; color: #0077b5 !important;
        border: 1px solid #0077b5; padding: 10px; border-radius: 5px; display: block; text-align: center; margin-top: 5px;
    }

    /* TEXTOS E INPUTS */
    h1, h2, h3 { color: #E5C365; font-family: 'Segoe UI', sans-serif; }
    p { color: #ccc; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        color: white; background-color: #262730; border: 1px solid #444;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. GERENCIAMENTO DE ESTADO
# ==============================================================================
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 'home'

def navegar_para(pagina):
    st.session_state.pagina_atual = pagina
    st.rerun()

# ==============================================================================
# 3. FUNÇÕES IA
# ==============================================================================
def criar_docx(texto):
    doc = Document()
    doc.add_heading('Documento Jurídico - Carmélio AI', 0)
    doc.add_paragraph(texto)
    doc.add_paragraph('\n\n___________________________________\nAssinatura')
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def get_gemini_response(prompt, file_data=None, mime_type=None, system_instruction="", anonimizar=False):
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ ERRO: Configure a chave no Secrets."
    model_name = "gemini-flash-latest"
    if anonimizar: system_instruction += "\n\nREGRA LGPD: Substitua nomes reais por [NOME], CPFs por [CPF]."
    content = []
    if file_data: content.append({"mime_type": mime_type, "data": file_data})
    if prompt: content.append(prompt)
    try:
        model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
        response = model.generate_content(content)
        return response.text
    except Exception as e: return f"❌ Erro: {str(e)}"

# ==============================================================================
# 4. BARRA LATERAL (COM SEU PERFIL E CONTATOS)
# ==============================================================================
with st.sidebar:
    st.markdown("# 🏛️ Carmélio AI")
    st.caption("Suite Jurídica & Cartorária")
    
    if st.button("🏠 MENU INICIAL"): navegar_para('home')
    
    st.markdown("---")
    
    # === ÁREA DO ESPECIALISTA (NOVO!) ===
    st.markdown("### 👨‍⚖️ O Especialista")
    st.info("**Arthur Carmélio**\n\nAdvogado, Escritor e Especialista em Registros Públicos.")
    
    # Botões de Link Externo
    st.markdown("""
    <a href="https://www.linkedin.com/in/arthurcarmelio/" target="_blank">
        👔 Conectar no LinkedIn
    </a>
    <a href="https://wa.me/5548920039720?text=Ol%C3%A1%20Arthur,%20vim%20pelo%20App%20e%20gostaria%20de%20falar%20sobre%20um%20servi%C3%A7o." target="_blank">
        💬 Chamar no WhatsApp
    </a>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🛡️ Configuração")
    modo_anonimo = st.toggle("Modo LGPD (Anonimizar)", value=False)
    termo_aceite = st.checkbox("Aceito processar dados.", value=True)

if not termo_aceite: st.stop()

# ==============================================================================
# 5. DASHBOARD (TELA INICIAL)
# ==============================================================================
if st.session_state.pagina_atual == 'home':
    st.title("🏛️ Painel de Ferramentas")
    
    # 3 Colunas de Ferramentas IA
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🤖 **Mentor Jurídico**")
        st.caption("Tira-dúvidas OAB/PCSC e correção de peças.")
        if st.button("ACESSAR MENTOR"): navegar_para('mentor')
        st.write("")
        st.success("📝 **Gerador de Contratos**")
        st.caption("Contratos de Imóveis, Veículos e Serviços.")
        if st.button("CRIAR CONTRATO"): navegar_para('contratos')
    with col2:
        st.warning("🏛️ **Cartório Digital**")
        st.caption("OCR: Transforme fotos de livros em Word.")
        if st.button("ABRIR CARTÓRIO"): navegar_para('cartorio')
        st.write("")
        st.error("🧠 **Como Funciona**")
        st.caption("Entenda a tecnologia por trás da IA.")
        if st.button("VER BASTIDORES"): navegar_para('tecnico')
    with col3:
        st.info("🎙️ **Transcrição de Áudio**")
        st.caption("Grave ditados e audiências.")
        if st.button("TRANSCREVER"): navegar_para('audio')
        
    st.markdown("---")
    
    # === ÁREA DE SERVIÇOS REAIS (NOVO!) ===
    st.subheader("🔍 Precisa de um Serviço Humano?")
    st.markdown("A IA ajuda, mas alguns casos exigem um especialista presencial.")
    
    c_serv1, c_serv2 = st.columns(2)
    with c_serv1:
        st.markdown("""
        <div style="background-color: #1e2530; padding: 20px; border-radius: 10px; border: 1px solid #444;">
            <h3>📜 Busca de Certidões</h3>
            <p>Precisa da via física ou busca em cartórios antigos?</p>
            <p style="color: #bbb;">• 2ª Via de Certidões<br>• Busca de Bens<br>• Regularização Imobiliária</p>
            <a href="https://wa.me/5548920039720?text=Ol%C3%A1,%20preciso%20de%20ajuda%20com%20Busca%20de%20Certid%C3%B5es." target="_blank" style="background: #25D366; color: white !important; border: none;">
                SOLICITAR BUSCA NO WHATSAPP
            </a>
        </div>
        """, unsafe_allow_html=True)
    
    with c_serv2:
        st.markdown("""
        <div style="background-color: #1e2530; padding: 20px; border-radius: 10px; border: 1px solid #444;">
            <h3>🤝 Assessoria Jurídica</h3>
            <p>Dúvidas complexas ou análise de casos concretos?</p>
            <p style="color: #bbb;">• Consultoria Civil<br>• Análise de Contratos<br>• Mentoria para OAB/Concursos</p>
            <a href="https://wa.me/5548920039720?text=Ol%C3%A1,%20gostaria%20de%20uma%20Consultoria%20Jur%C3%ADdica." target="_blank" style="background: #25D366; color: white !important; border: none;">
                FALAR COM ARTHUR
            </a>
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# MÓDULOS (CONTRATOS, MENTOR, CARTÓRIO, ÁUDIO, TÉCNICO)
# ==============================================================================
elif st.session_state.pagina_atual == 'contratos':
    st.title("📝 Gerador de Contratos")
    if st.button("⬅️ Voltar"): navegar_para('home')
    st.markdown("---")
    col_tipo, _ = st.columns(2)
    tipo = col_tipo.selectbox("Tipo:", ["Aluguel Residencial", "Compra e Venda Veículo", "Prestação Serviços", "Honorários", "Personalizado"])
    c1, c2 = st.columns(2)
    a = c1.text_input("Parte A (Contratante):")
    b = c2.text_input("Parte B (Contratado):")
    obj = c1.text_area("Objeto:")
    val = c2.text_area("Valor/Condições:")
    extra = st.text_input("Cláusulas Extras:")
    if st.button("🚀 GERAR MINUTA"):
        with st.spinner("Redigindo..."):
            prompt = f"Redija um CONTRATO DE {tipo} completo. Parte A: {a}, Parte B: {b}, Objeto: {obj}, Valor: {val}, Extras: {extra}. Use juridiquês formal."
            resp = get_gemini_response(prompt, anonimizar=modo_anonimo)
            st.write(resp)
            st.download_button("💾 Baixar", criar_docx(resp), f"Contrato_{tipo}.docx")

elif st.session_state.pagina_atual == 'mentor':
    st.title("🤖 Mentor Jurídico")
    if st.button("⬅️ Voltar"): navegar_para('home')
    modo = st.radio("Modo:", ["OAB", "PCSC"], horizontal=True)
    inst = "Seja examinador OAB." if "OAB" in modo else "Seja mentor policial."
    if 'chat_mentor' not in st.session_state: st.session_state.chat_mentor = []
    for m in st.session_state.chat_mentor: st.chat_message(m['role']).write(m['content'])
    if p := st.chat_input("Dúvida..."):
        st.session_state.chat_mentor.append({"role":"user", "content":p})
        st.chat_message("user").write(p)
        with st.chat_message("assistant"):
            r = get_gemini_response(p, system_instruction=inst, anonimizar=modo_anonimo)
            st.write(r)
            st.session_state.chat_mentor.append({"role":"assistant", "content":r})

elif st.session_state.pagina_atual == 'cartorio':
    st.title("🏛️ Cartório Digital")
    if st.button("⬅️ Voltar"): navegar_para('home')
    up = st.file_uploader("Imagem/PDF", type=["jpg","png","pdf"])
    if up and st.button("📝 EXTRAIR"):
        with st.spinner("Lendo..."):
            r = get_gemini_response("Inteiro Teor.", file_data=up.getvalue(), mime_type=up.type, anonimizar=modo_anonimo)
            st.text_area("Texto:", r, height=400)
            st.download_button("💾 Baixar Word", criar_docx(r), "InteiroTeor.docx")

elif st.session_state.pagina_atual == 'audio':
    st.title("🎙️ Transcrição")
    if st.button("⬅️ Voltar"): navegar_para('home')
    t1, t2 = st.tabs(["Gravar", "Upload"])
    ad=None; mime=None
    with t1:
        if r:=st.audio_input("Gravar"): ad=r.getvalue(); mime="audio/wav"
    with t2:
        if u:=st.file_uploader("Arquivo", type=["mp3","wav","m4a"]): ad=u.getvalue(); mime=u.type
    if ad and st.button("TRANSCREVER"):
        with st.spinner("Processando..."):
            r = get_gemini_response("Transcreva.", file_data=ad, mime_type=mime, anonimizar=modo_anonimo)
            st.write(r)
            st.download_button("💾 Baixar Word", criar_docx(r), "Transcricao.docx")

elif st.session_state.pagina_atual == 'tecnico':
    st.title("🧠 Bastidores")
    if st.button("⬅️ Voltar"): navegar_para('home')
    st.info("Sistema baseado em Google Gemini (Transformer Architecture).")
    st.code("model = genai.GenerativeModel('gemini-flash-latest')", language="python")
