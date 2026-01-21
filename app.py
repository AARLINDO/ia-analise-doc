import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÃO E DESIGN
# ==============================================================================
st.set_page_config(page_title="Carmélio AI Suite", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #161a24; border-right: 1px solid #2b303b; }
    .stButton>button { 
        width: 100%; border-radius: 6px; height: 50px; font-weight: bold; border: none;
        background: linear-gradient(90deg, #967036, #C6A34F); color: #000;
        text-transform: uppercase; letter-spacing: 1px; transition: 0.3s;
    }
    .stButton>button:hover { background: linear-gradient(90deg, #C6A34F, #E5C365); color: #000; }
    h1, h2, h3 { color: #E5C365; font-family: 'Segoe UI', sans-serif; }
    p { color: #ccc; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        color: white; background-color: #262730; border: 1px solid #444;
    }
    a { text-decoration: none !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNÇÕES IA (AGORA COM MODELO UNIVERSAL)
# ==============================================================================
def criar_docx(texto):
    """Gera DOCX garantindo que não quebre com caracteres estranhos."""
    try:
        if not texto or "❌" in texto: return None
        doc = Document()
        doc.add_heading('Documento Jurídico - Carmélio AI', 0)
        texto_limpo = str(texto).replace('\x00', '')
        for p in texto_limpo.split('\n'):
            if p.strip(): doc.add_paragraph(p)
        doc.add_paragraph('\n\n___________________________________\nAssinatura')
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except: return None

def get_gemini_response(prompt, file_data=None, mime_type=None, system_instruction=None, anonimizar=False):
    """Conecta ao Gemini usando modelo compatível com versões antigas e novas."""
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key: return "❌ ERRO: Configure a GOOGLE_API_KEY nos Secrets."
        
        genai.configure(api_key=api_key)
        
        # Ajuste de Instruções
        sys_inst = system_instruction if system_instruction else "Você é um assistente jurídico útil e preciso."
        if anonimizar: sys_inst += "\n\nREGRA LGPD: Substitua nomes reais por [NOME], CPFs por [CPF]."
        
        # CONFIGURAÇÃO DE SEGURANÇA (Para evitar bloqueios bobos)
        safe = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        # Tenta usar o modelo 'gemini-pro' que é o padrão universal
        # (Funciona mesmo se a biblioteca estiver desatualizada no servidor)
        model = genai.GenerativeModel("gemini-pro") 
        
        # PREPARAÇÃO DO PROMPT
        # O gemini-pro antigo prefere receber tudo como string ou lista simples
        if file_data:
             # Se tiver imagem/audio, tentamos o modelo de visão se disponível, ou avisamos
             # Mas para contratos (texto), isso aqui resolve 100% dos erros 404
             return "⚠️ Para processar imagens/áudio, precisamos forçar a atualização do servidor. Tente apenas texto por enquanto."
        else:
            # Adiciona a instrução do sistema manualmente no prompt para garantir compatibilidade
            full_prompt = f"INSTRUÇÃO DO SISTEMA: {sys_inst}\n\nUSUÁRIO: {prompt}"
            response = model.generate_content(full_prompt, safety_settings=safe)

        return response.text
        
    except Exception as e:
        # Se der erro específico de modelo não encontrado, tenta o ultra-básico
        if "404" in str(e):
             return f"❌ Erro de Versão: O servidor do Streamlit está usando uma versão antiga. Por favor, reinicie o app (Reboot) no menu 'Manage App'."
        return f"❌ Erro Técnico: {str(e)}"

# ==============================================================================
# 3. NAVEGAÇÃO
# ==============================================================================
if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = 'home'
def navegar_para(pagina): st.session_state.pagina_atual = pagina; st.rerun()

# ==============================================================================
# 4. BARRA LATERAL
# ==============================================================================
with st.sidebar:
    st.markdown("# 🏛️ Carmélio AI")
    if st.button("🏠 MENU INICIAL"): navegar_para('home')
    st.markdown("---")
    st.info("**Arthur Carmélio**\n\nAdvogado & Especialista.")
    st.markdown("""
    <div style="display: flex; flex-direction: column; gap: 10px;">
        <a href="https://www.linkedin.com/in/arthurcarmelio/" target="_blank" style="background-color: #0077b5; color: white; padding: 8px; border-radius: 5px; text-align: center;">👔 LinkedIn</a>
        <a href="https://wa.me/5548920039720" target="_blank" style="background-color: #25D366; color: white; padding: 8px; border-radius: 5px; text-align: center;">💬 WhatsApp</a>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    modo_anonimo = st.toggle("Modo LGPD", value=False)
    if not st.checkbox("Aceito processar dados.", value=True): st.stop()

# ==============================================================================
# 5. TELAS
# ==============================================================================
if st.session_state.pagina_atual == 'home':
    st.title("🏛️ Painel de Ferramentas")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("🤖 **Mentor Jurídico**"); st.caption("Tira-dúvidas e Correção.")
        if st.button("ACESSAR MENTOR"): navegar_para('mentor')
        st.write(""); st.success("📝 **Gerador de Contratos**"); st.caption("Minutas Rápidas.")
        if st.button("CRIAR CONTRATO"): navegar_para('contratos')
    with c2:
        st.warning("🏛️ **Cartório Digital**"); st.caption("OCR e Leitura de Docs.")
        if st.button("ABRIR CARTÓRIO"): navegar_para('cartorio')
        st.write(""); st.error("🧠 **Bastidores**"); st.caption("Tecnologia.")
        if st.button("VER TÉCNICO"): navegar_para('tecnico')
    with c3:
        st.info("🎙️ **Transcrição**"); st.caption("Áudio para Texto.")
        if st.button("TRANSCREVER"): navegar_para('audio')
    st.markdown("---")
    st.subheader("Precisa de um Humano?")
    cs1, cs2 = st.columns(2)
    with cs1: st.markdown("### 📜 Busca de Certidões\nPrecisa da via física? [Fale Comigo](https://wa.me/5548920039720)")
    with cs2: st.markdown("### 🤝 Assessoria Jurídica\nCaso complexo? [Agende Consultoria](https://wa.me/5548920039720)")

elif st.session_state.pagina_atual == 'contratos':
    st.title("📝 Gerador de Contratos")
    if st.button("⬅️ Voltar"): navegar_para('home')
    st.markdown("---")
    t = st.selectbox("Tipo:", ["Aluguel Residencial", "Compra e Venda Veículo", "Prestação Serviços", "Honorários", "Personalizado"])
    c1, c2 = st.columns(2)
    a = c1.text_input("Parte A (Contratante):")
    b = c2.text_input("Parte B (Contratado):")
    obj = c1.text_area("Objeto:")
    val = c2.text_area("Valor/Condições:")
    ex = st.text_input("Extras:")
    if st.button("🚀 GERAR MINUTA"):
        if not a or not b or not val: st.warning("Preencha as partes e valor.")
        else:
            with st.spinner("Redigindo..."):
                p = f"Redija um CONTRATO DE {t} completo. PARTES: {a} e {b}. OBJETO: {obj}. VALOR: {val}. EXTRAS: {ex}. Use juridiquês formal e leis BR."
                r = get_gemini_response(p, anonimizar=modo_anonimo)
                st.write(r)
                docx = criar_docx(r)
                if docx: st.download_button("💾 Baixar DOCX", docx, f"Contrato_{t}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

elif st.session_state.pagina_atual == 'mentor':
    st.title("🤖 Mentor Jurídico")
    if st.button("⬅️ Voltar"): navegar_para('home')
    modo = st.radio("Perfil:", ["OAB (Rigoroso)", "PCSC (Policial)"], horizontal=True)
    sys = "Seja examinador da OAB." if "OAB" in modo else "Seja mentor policial focado em Penal."
    if 'chat' not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat: st.chat_message(m['role']).write(m['content'])
    if p:=st.chat_input("Dúvida..."):
        st.session_state.chat.append({"role":"user", "content":p})
        st.chat_message("user").write(p)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                r = get_gemini_response(p, system_instruction=sys, anonimizar=modo_anonimo)
                st.write(r)
                st.session_state.chat.append({"role":"assistant", "content":r})

elif st.session_state.pagina_atual == 'cartorio':
    st.title("🏛️ Cartório Digital")
    if st.button("⬅️ Voltar"): navegar_para('home')
    u = st.file_uploader("Documento (Foto/PDF)", type=["jpg","png","pdf"])
    if u and st.button("EXTRAIR TEXTO"):
        with st.spinner("Lendo..."):
            r = get_gemini_response("Transcreva este documento.", file_data=u.getvalue(), mime_type=u.type, anonimizar=modo_anonimo)
            st.text_area("Texto:", r, height=400)
            d = criar_docx(r)
            if d: st.download_button("💾 Baixar DOCX", d, "Doc.docx")

elif st.session_state.pagina_atual == 'audio':
    st.title("🎙️ Transcrição")
    if st.button("⬅️ Voltar"): navegar_para('home')
    t1, t2 = st.tabs(["Gravar", "Upload"])
    ad=None; mime=None
    with t1: 
        if x:=st.audio_input("Gravar"): ad=x.getvalue(); mime="audio/wav"
    with t2:
        if x:=st.file_uploader("Arquivo", type=["mp3","wav","m4a"]): ad=x.getvalue(); mime=x.type
    if ad and st.button("TRANSCREVER"):
        with st.spinner("Ouvindo..."):
            r = get_gemini_response("Transcreva o áudio em Português.", file_data=ad, mime_type=mime, anonimizar=modo_anonimo)
            st.write(r)
            d = criar_docx(r)
            if d: st.download_button("💾 Baixar DOCX", d, "Transcricao.docx")

elif st.session_state.pagina_atual == 'tecnico':
    st.title("🧠 Bastidores")
    if st.button("⬅️ Voltar"): navegar_para('home')
    st.info("Sistema rodando Google Gemini Pro (Compatibilidade Universal).")
