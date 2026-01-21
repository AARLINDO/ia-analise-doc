import streamlit as st
from groq import Groq
from docx import Document
from io import BytesIO
import base64
import os

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
# 2. FUNÇÕES IA (GROQ / LLAMA 3)
# ==============================================================================
def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key: return None, "❌ Erro: Chave GROQ_API_KEY não encontrada nos Secrets."
    return Groq(api_key=api_key), None

def criar_docx(texto):
    """Gera DOCX formatado."""
    try:
        if not texto or "❌" in texto: return None
        doc = Document()
        # Título
        doc.add_heading('CONTRATO JURÍDICO', 0)
        
        texto_limpo = str(texto).replace('\x00', '')
        for p in texto_limpo.split('\n'):
            if p.strip(): 
                paragraph = doc.add_paragraph(p)
                # Tenta identificar cláusulas para negrito (básico)
                if p.upper().startswith("CLÁUSULA") or p.upper().startswith("PARÁGRAFO"):
                    paragraph.runs[0].bold = True
                    
        doc.add_paragraph('\n\n___________________________________\nAssinatura do Contratante')
        doc.add_paragraph('\n___________________________________\nAssinatura do Contratado')
        doc.add_paragraph('\n___________________________________\nTestemunha 1')
        doc.add_paragraph('\n___________________________________\nTestemunha 2')
        
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
                tmp.write(file_bytes)
                tmp_path = tmp.name
            with open(tmp_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), file.read()),
                    model="whisper-large-v3", response_format="text", language="pt"
                )
            os.unlink(tmp_path)
            return transcription

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
                model="llama-3.2-11b-vision-preview", temperature=0.1,
            )
            return chat_completion.choices[0].message.content

        else:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile", temperature=0.5,
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
# 5. TELAS DO SISTEMA
# ==============================================================================
if st.session_state.pagina_atual == 'home':
    st.title("🏛️ Painel de Ferramentas")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("🤖 **Mentor Jurídico**"); st.caption("Tira-dúvidas e Correção.")
        if st.button("ACESSAR MENTOR"): navegar_para('mentor')
        st.write(""); st.success("📝 **Gerador de Contratos**"); st.caption("Modelo Personalizado.")
        if st.button("CRIAR CONTRATO"): navegar_para('contratos')
    with c2:
        st.warning("🏛️ **Cartório Digital**"); st.caption("OCR e Leitura de Docs.")
        if st.button("ABRIR CARTÓRIO"): navegar_para('cartorio')
        st.write(""); st.error("🧠 **Bastidores**"); st.caption("Tecnologia Groq.")
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
    st.title("📝 Gerador de Contratos (Modelo Personalizado)")
    if st.button("⬅️ Voltar"): navegar_para('home')
    st.markdown("---")
    
    t = st.selectbox("Tipo:", ["Aluguel Residencial", "Aluguel Comercial", "Compra e Venda", "Prestação de Serviços"])
    c1, c2 = st.columns(2)
    a = c1.text_input("LOCADOR / CONTRATANTE (Nome, CPF, Endereço):")
    b = c2.text_input("LOCATÁRIO / CONTRATADO (Nome, CPF, Endereço):")
    obj = c1.text_area("OBJETO DO CONTRATO (Descrição do Imóvel/Serviço):")
    val = c2.text_area("VALOR E PAGAMENTO (Ex: R$ 1.400,00 dia 20):")
    prazo = st.text_input("PRAZO (Ex: 24 meses, Início 01/01/2025):")
    ex = st.text_input("CLÁUSULAS EXTRAS (Opcional):")
    
    if st.button("🚀 GERAR MINUTA ABNT"):
        if not a or not b or not val: st.warning("Preencha as partes e valor.")
        else:
            with st.spinner("Redigindo com base no seu modelo..."):
                # AQUI ESTÁ A MÁGICA: O TEMPLATE DO SEU PDF INSERIDO NO CÓDIGO
                template_base = """
                ESTRUTURA PADRÃO OBRIGATÓRIA (Baseada no Modelo Darlene/Manoel):
                1. CABEÇALHO: Título em CAIXA ALTA (ex: CONTRATO DE LOCAÇÃO).
                2. QUALIFICAÇÃO: "Os signatários deste instrumento..." com dados completos (Nome, Nacionalidade, CPF, RG, Endereço).
                3. CLÁUSULA PRIMEIRA - DO OBJETO: Descrição detalhada do imóvel/serviço.
                4. CLÁUSULA SEGUNDA - DO PRAZO: Duração, datas de início e fim.
                5. CLÁUSULA TERCEIRA - DO VALOR: Valor total, parcelamento, datas de vencimento. Citar Caução se houver.
                   - Parágrafo Único: Multa de 10% e Juros de 1% ao mês em caso de atraso.
                6. CLÁUSULA QUARTA - REAJUSTE: Índice anual (IGPM ou INPC).
                7. CLÁUSULA QUINTA - DESTINAÇÃO: (Comercial ou Residencial). Proibição de sublocação.
                8. CLÁUSULA SEXTA - CONSERVAÇÃO E BENFEITORIAS: Vistoria prévia, devolução no mesmo estado, benfeitorias incorporadas sem indenização.
                9. CLÁUSULA SÉTIMA - VISTORIA: Direito do Locador vistoriar. Prazo de 5 dias para reparos.
                10. CLÁUSULA OITAVA - DO FORO: Eleição da comarca local.
                11. FECHAMENTO: "E por estarem justos e contratados...", Cidade, Data.
                12. ASSINATURAS: Linhas para Locador, Locatário e 2 Testemunhas.
                """
                
                prompt = f"""
                Atue como um Tabelião Jurídico. Redija um {t} seguindo RIGOROSAMENTE a estrutura abaixo:
                
                {template_base}
                
                DADOS DO CASO REAL:
                - LOCADOR: {a}
                - LOCATÁRIO: {b}
                - OBJETO: {obj}
                - VALOR: {val}
                - PRAZO: {prazo}
                - EXTRAS: {ex}
                
                Se houver dados faltando (como RG ou Endereço exato), deixe um espaço entre colchetes [PREENCHER] para o usuário completar depois.
                """
                
                if modo_anonimo: prompt += " SUBSTITUA NOMES REAIS POR [NOME]."
                
                r = processar_ia(prompt, task_type="text")
                st.write(r)
                docx = criar_docx(r)
                if docx: st.download_button("💾 Baixar Minuta (.docx)", docx, f"Contrato_{t}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

elif st.session_state.pagina_atual == 'mentor':
    st.title("🤖 Mentor Jurídico")
    if st.button("⬅️ Voltar"): navegar_para('home')
    modo = st.radio("Perfil:", ["OAB (Rigoroso)", "PCSC (Policial)"], horizontal=True)
    sys = "Atue como examinador da OAB, cite artigos." if "OAB" in modo else "Atue como mentor policial focado em Penal."
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
    st.success("Sistema rodando na Groq com Llama 3 (Template Personalizado).")
