import streamlit as st
from groq import Groq
from docx import Document
from io import BytesIO
import base64

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
# 2. FUNÇÕES IA (MIGRADO PARA GROQ - MAIS RÁPIDO E ESTÁVEL)
# ==============================================================================
def get_groq_client():
    """Pega a chave da Groq de forma segura."""
    api_key = st.secrets.get("GROQ_API_KEY")
    # Fallback: Tenta pegar a do Google se a da Groq não estiver definida (improvável, mas seguro)
    if not api_key:
        return None, "❌ Erro: Chave GROQ_API_KEY não encontrada nos Secrets."
    return Groq(api_key=api_key), None

def criar_docx(texto):
    """Gera DOCX garantindo que não quebre."""
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

def processar_ia(prompt, file_bytes=None, task_type="text", system_instruction="Você é um assistente útil."):
    """Função Universal da Groq para Texto, Visão e Áudio."""
    client, erro = get_groq_client()
    if erro: return erro

    try:
        # 1. TRANSCRIÇÃO DE ÁUDIO (Whisper)
        if task_type == "audio" and file_bytes:
            # Groq precisa de um nome de arquivo para saber o formato
            import tempfile, os
            suffix = ".mp3" # Padrão seguro
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            
            with open(tmp_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), file.read()),
                    model="whisper-large-v3",
                    response_format="text",
                    language="pt"
                )
            os.unlink(tmp_path) # Limpa temp
            return transcription

        # 2. VISÃO (OCR/Leitura de Docs)
        elif task_type == "vision" and file_bytes:
            base64_image = base64.b64encode(file_bytes).decode('utf-8')
            chat_completion = client.chat.completions.create(
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                model="llama-3.2-11b-vision-preview",
                temperature=0.1,
            )
            return chat_completion.choices[0].message.content

        # 3. TEXTO (Contratos/Chat)
        else:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile", # Modelo mais inteligente atual
                temperature=0.5,
            )
            return chat_completion.choices[0].message.content

    except Exception as e:
        return f"❌ Erro na IA: {str(e)}"

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
            with st.spinner("Redigindo com Llama 3..."):
                sys = "Você é um advogado especialista em Direito Civil Brasileiro."
                p = f"Redija um CONTRATO DE {t} completo. PARTES: {a} e {b}. OBJETO: {obj}. VALOR: {val}. EXTRAS: {ex}. Use juridiquês formal, leis do Brasil e foro de eleição."
                if modo_anonimo: p += " Anonimize dados pessoais."
                
                r = processar_ia(p, task_type="text", system_instruction=sys)
                st.write(r)
                docx = criar_docx(r)
                if docx: st.download_button("💾 Baixar DOCX", docx, f"Contrato_{t}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

elif st.session_state.pagina_atual == 'mentor':
    st.title("🤖 Mentor Jurídico")
    if st.button("⬅️ Voltar"): navegar_para('home')
    modo = st.radio("Perfil:", ["OAB (Rigoroso)", "PCSC (Policial)"], horizontal=True)
    sys = "Atue como examinador da OAB, cite artigos." if "OAB" in modo else "Atue como mentor policial focado em Penal e Administrativo."
    if 'chat' not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat: st.chat_message(m['role']).write(m['content'])
    if p:=st.chat_input("Dúvida..."):
        st.session_state.chat.append({"role":"user", "content":p})
        st.chat_message("user").write(p)
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                r = processar_ia(p, task_type="text", system_instruction=sys)
                st.write(r)
                st.session_state.chat.append({"role":"assistant", "content":r})

elif st.session_state.pagina_atual == 'cartorio':
    st.title("🏛️ Cartório Digital")
    if st.button("⬅️ Voltar"): navegar_para('home')
    u = st.file_uploader("Documento (Foto/PDF)", type=["jpg","png","jpeg","pdf"])
    if u and st.button("EXTRAIR TEXTO"):
        with st.spinner("Lendo documento com Visão Computacional..."):
            p = "Transcreva todo o texto desta imagem fielmente. Mantenha formatação."
            r = processar_ia(p, file_bytes=u.getvalue(), task_type="vision")
            st.text_area("Texto:", r, height=400)
            d = criar_docx(r)
            if d: st.download_button("💾 Baixar DOCX", d, "Doc.docx")

elif st.session_state.pagina_atual == 'audio':
    st.title("🎙️ Transcrição")
    if st.button("⬅️ Voltar"): navegar_para('home')
    t1, t2 = st.tabs(["Gravar", "Upload"])
    ad=None
    with t1: 
        if x:=st.audio_input("Gravar"): ad=x.getvalue()
    with t2:
        if x:=st.file_uploader("Arquivo", type=["mp3","wav","m4a"]): ad=x.getvalue()
    if ad and st.button("TRANSCREVER"):
        with st.spinner("Ouvindo com Whisper..."):
            r = processar_ia("", file_bytes=ad, task_type="audio")
            st.write(r)
            d = criar_docx(r)
            if d: st.download_button("💾 Baixar DOCX", d, "Transcricao.docx")

elif st.session_state.pagina_atual == 'tecnico':
    st.title("🧠 Bastidores")
    if st.button("⬅️ Voltar"): navegar_para('home')
    st.success("Sistema atualizado para engine **Groq (Llama 3.3)** - Alta velocidade.")
    st.code("client = Groq(api_key=secrets['GROQ_API_KEY'])\nmodel = 'llama-3.3-70b-versatile'", language="python")
