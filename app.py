import streamlit as st
import os
import json
import time
import re
from datetime import datetime
from io import BytesIO

# =============================================================================
# 1. CONFIGURAÇÃO
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Gemini Edition",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 2. IMPORTAÇÕES
# =============================================================================
try: import google.generativeai as genai
except ImportError: genai = None

try: import pdfplumber
except ImportError: pdfplumber = None

try: 
    import docx
    from docx import Document
except ImportError: 
    docx = None
    Document = None

try: from PIL import Image
except ImportError: Image = None

# =============================================================================
# 3. FUNÇÕES UTILITÁRIAS
# =============================================================================

def safe_image_show(image_path):
    if os.path.exists(image_path):
        try: st.image(image_path, use_container_width=True)
        except TypeError: st.image(image_path, use_column_width=True)
    else: st.markdown("## ⚖️ Carmélio AI")

def get_audio_input_safe(label):
    if hasattr(st, "audio_input"): return st.audio_input(label)
    st.warning("⚠️ Gravação direta indisponível. Use o Upload."); return None

def check_rate_limit():
    if "last_call" not in st.session_state: st.session_state.last_call = 0
    now = time.time()
    if now - st.session_state.last_call < 1.0: return True
    return False

def mark_call(): st.session_state.last_call = time.time()

# =============================================================================
# 4. MOTOR DE IA (GOOGLE GEMINI 1.5 FLASH)
# =============================================================================
@st.cache_resource
def get_gemini_model():
    """Configura e retorna o modelo Gemini uma única vez."""
    # Tenta pegar a chave do secrets ou do ambiente
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not api_key: return None
    
    try:
        genai.configure(api_key=api_key)
        # Tenta o modelo Flash (mais rápido e contexto maior)
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        # Se der erro, tenta o Pro como fallback
        try:
            return genai.GenerativeModel('gemini-pro')
        except:
            st.error(f"Erro Crítico ao conectar no Google: {e}")
            return None

def call_gemini(system_prompt, user_prompt, json_mode=False):
    """Função única para chamar o Google."""
    if check_rate_limit(): return None
    mark_call()
    
    model = get_gemini_model()
    if not model: return "⚠️ Erro: Chave API do Google não configurada no secrets.toml."
    
    try:
        # Gemini funciona melhor com um prompt único concatenado
        full_prompt = f"SISTEMA: {system_prompt}\n\nUSUÁRIO: {user_prompt}"
        
        if json_mode:
            full_prompt += "\n\nIMPORTANTE: Responda APENAS com um JSON válido. Não use blocos de código (```json)."
            
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Erro na IA: {str(e)}"

def extract_json_surgical(text):
    """Limpeza de resposta para garantir JSON válido."""
    try:
        text = text.replace("```json", "").replace("```", "")
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match: return json.loads(match.group(0))
    except: pass
    return None

# =============================================================================
# 5. PROCESSAMENTO DE ARQUIVOS
# =============================================================================
def read_pdf_safe(file_obj):
    if not pdfplumber: return "Erro: Biblioteca PDF ausente."
    try:
        with pdfplumber.open(BytesIO(file_obj.getvalue())) as pdf:
            return "".join([p.extract_text() or "" for p in pdf.pages])
    except Exception as e: return f"Erro PDF: {str(e)}"

def markdown_to_docx(doc_obj, text):
    if not text: return
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith('# '): doc_obj.add_heading(line[2:], 0)
        elif line.startswith('## '): doc_obj.add_heading(line[3:], 1)
        else: doc_obj.add_paragraph(line)

def create_contract_docx(clauses, meta):
    if not docx: return None
    doc = Document()
    doc.add_heading(meta.get('tipo', 'CONTRATO').upper(), 0)
    doc.add_heading("1. QUALIFICAÇÃO", level=1)
    doc.add_paragraph(meta.get('partes', ''))
    doc.add_heading("2. DO OBJETO", level=1)
    doc.add_paragraph(meta.get('objeto', ''))
    for clause in clauses:
        doc.add_heading(clause.get('titulo', 'Cláusula'), level=1)
        markdown_to_docx(doc, clause.get('conteudo', ''))
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# =============================================================================
# 6. UI & ESTADO
# =============================================================================
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #11141d; border-right: 1px solid #2B2F3B; }
    .gemini-text {
        background: -webkit-linear-gradient(45deg, #4285F4, #9B72CB, #D96570);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.2rem;
    }
    .clause-card {
        background-color: #1F2430; border: 1px solid #374151;
        border-radius: 12px; padding: 20px; margin-bottom: 15px;
    }
    div.stButton > button {
        background: linear-gradient(90deg, #2563EB 0%, #7C3AED 100%);
        color: white; border: none; font-weight: 600; border-radius: 8px;
    }
    .footer-credits { text-align: center; margin-top: 40px; color: #6B7280; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# Inicializa Variáveis
if "user_xp" not in st.session_state: st.session_state.user_xp = 0
if "contract_step" not in st.session_state: st.session_state.contract_step = 1
if "contract_clauses" not in st.session_state: st.session_state.contract_clauses = []
if "contract_meta" not in st.session_state: st.session_state.contract_meta = {}
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "edital_text" not in st.session_state: st.session_state.edital_text = ""
if "last_question" not in st.session_state: st.session_state.last_question = None 

def add_xp(amount):
    st.session_state.user_xp += amount
    st.toast(f"+{amount} XP | Nível {int(st.session_state.user_xp/100)}", icon="⚡")

# =============================================================================
# 7. APLICAÇÃO PRINCIPAL
# =============================================================================
with st.sidebar:
    safe_image_show("logo.jpg.png")
    
    st.success("🧠 **Gemini 1.5 Ativo**")
    
    st.markdown("---")
    menu = st.radio("Navegação", [
        "✨ Chat Inteligente", 
        "📝 Redação Pro", 
        "🎯 Mestre dos Editais", 
        "🍅 Sala de Foco", 
        "🏢 Cartório OCR", 
        "🎙️ Transcrição"
    ], label_visibility="collapsed")
    
    st.markdown("---")
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))
    st.markdown(f"<small>Nível {int(st.session_state.user_xp/100)} | {st.session_state.user_xp} XP</small>", unsafe_allow_html=True)
    st.markdown("""<div class='footer-credits'>Arthur Carmélio</div>""", unsafe_allow_html=True)

# --- 1. CHAT ---
if menu == "✨ Chat Inteligente":
    st.markdown('<h1 class="gemini-text">Mentor Jurídico</h1>', unsafe_allow_html=True)
    if not st.session_state.chat_history:
        st.info("Olá! Sou o Carmélio AI. Estou conectado à legislação brasileira atualizada.")
        
    for msg in st.session_state.chat_history:
        avatar = "🧑‍⚖️" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar): st.markdown(msg["content"])
        
    if p := st.chat_input("Digite sua dúvida..."):
        st.session_state.chat_history.append({"role": "user", "content": p})
        with st.chat_message("user", avatar="🧑‍⚖️"): st.write(p)
        
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analisando..."):
                # Contexto das últimas mensagens para memória
                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history[-6:]])
                
                res = call_gemini(
                    "Você é um Advogado Sênior e Professor de Direito. Responda com base na CF/88, CC, CPC e Jurisprudência. Seja didático.", 
                    history
                )
                st.write(res)
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                add_xp(5)

# --- 2. REDAÇÃO ---
elif menu == "📝 Redação Pro":
    step = st.session_state.contract_step
    
    # Barra de Progresso
    c1, c2, c3 = st.columns([1,1,1])
    c1.markdown(f"**1. Dados** {'✅' if step > 1 else '🟦'}")
    c2.markdown(f"**2. Estrutura** {'✅' if step > 2 else ('🟦' if step==2 else '⬜')}")
    c3.markdown(f"**3. Revisão** {'✅' if step > 3 else ('🟦' if step==3 else '⬜')}")
    st.progress(int(step/3 * 100))

    if step == 1:
        st.header("📝 Detalhes")
        with st.container(border=True):
            tipo = st.text_input("Tipo de Documento", placeholder="Ex: Contrato de Honorários")
            partes = st.text_area("Partes", placeholder="Qualificação completa...")
            objeto = st.text_area("Objeto", placeholder="Detalhes do serviço/acordo...")
            
            if st.button("Gerar Estrutura ➔", type="primary", use_container_width=True):
                if tipo and objeto:
                    with st.spinner("Gemini desenhando o contrato..."):
                        prompt = f"Crie a estrutura de um {tipo}. Partes: {partes}. Objeto: {objeto}. Retorne JSON com lista de cláusulas (titulo, conteudo)."
                        res = call_gemini("Gere APENAS JSON válido.", prompt, json_mode=True)
                        data = extract_json_surgical(res)
                        
                        if data and 'clauses' in data:
                            st.session_state.contract_meta = {"tipo": tipo, "partes": partes, "objeto": objeto}
                            st.session_state.contract_clauses = data['clauses']
                            st.session_state.contract_step = 2
                            add_xp(20)
                            st.rerun()
                        else: st.error("Erro ao estruturar. Tente detalhar mais.")
                else: st.warning("Preencha todos os campos.")

    elif step == 2:
        st.header("📑 Editor")
        if st.button("➕ Nova Cláusula"):
            st.session_state.contract_clauses.append({"titulo": "Nova", "conteudo": "..."})
            st.rerun()

        to_remove = []
        for i, c in enumerate(st.session_state.contract_clauses):
            with st.expander(f"{i+1}. {c.get('titulo')}", expanded=False):
                new_t = st.text_input(f"Título", c.get('titulo'), key=f"t_{i}") 
                new_c = st.text_area(f"Texto", c.get('conteudo'), height=200, key=f"c_{i}")
                st.session_state.contract_clauses[i] = {"titulo": new_t, "conteudo": new_c}
                if st.button("🗑️ Excluir", key=f"d_{i}"): to_remove.append(i)
        
        if to_remove:
            for i in sorted(to_remove, reverse=True): del st.session_state.contract_clauses[i]
            st.rerun()

        c1, c2 = st.columns([1, 2])
        if c1.button("⬅️ Voltar"): 
            st.session_state.contract_step = 1
            st.rerun()
        if c2.button("Finalizar ➔", type="primary", use_container_width=True):
            st.session_state.contract_step = 3
            st.rerun()

    elif step == 3:
        st.header("✅ Finalização")
        c_view, c_chat = st.columns([2, 1])
        
        with c_view:
            docx = create_contract_docx(st.session_state.contract_clauses, st.session_state.contract_meta)
            if docx:
                st.download_button("💾 BAIXAR DOCX", docx, "Minuta.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary", use_container_width=True)
            
            full_text = f"# {st.session_state.contract_meta.get('tipo')}\n\n"
            for c in st.session_state.contract_clauses: full_text += f"## {c['titulo']}\n{c['conteudo']}\n\n"
            st.text_area("Preview", full_text, height=600)
            
            if st.button("✏️ Editar"): 
                st.session_state.contract_step = 2
                st.rerun()
                
        with c_chat:
            st.info("Precisa de ajustes?")
            q = st.text_input("Ex: 'Adicione foro de eleição'")
            if q:
                with st.spinner("Reescrevendo..."):
                    ans = call_gemini("Revisor Jurídico.", f"Texto atual: {full_text}\nPedido: {q}")
                    st.write(ans)

# --- 3. EDITAIS ---
elif menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais")
    f = st.file_uploader("Upload PDF (Até 200MB)", type=["pdf"])
    
    if f:
        with st.spinner("Gemini lendo arquivo..."):
            st.session_state.edital_text = read_pdf_safe(f)
        st.success("Lido com sucesso!")
        
    if st.session_state.edital_text:
        if st.button("📝 Gerar Questão de Prova"):
            with st.spinner("Criando questão difícil..."):
                prompt = f"Ignore regras de inscrição. FOQUE NO CONTEÚDO PROGRAMÁTICO. Crie uma questão difícil de concurso sobre o texto: {st.session_state.edital_text[:30000]}"
                st.session_state.last_question = call_gemini("Examinador de Banca.", prompt)
                add_xp(15)
        
        if st.session_state.last_question:
            st.markdown(f"<div class='clause-card'>{st.session_state.last_question}</div>", unsafe_allow_html=True)

# --- 4. EXTRAS ---
elif menu == "🍅 Sala de Foco":
    st.title("🍅 Foco")
    if st.button("Iniciar 25m", type="primary"): st.success("Timer Iniciado!")

elif menu == "🏢 Cartório OCR":
    st.title("🏢 OCR")
    u = st.file_uploader("Imagem/PDF")
    if u: st.info("OCR pronto para processar.")

elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição")
    u = st.file_uploader("Áudio")
    if u: st.info("Áudio pronto para processar.")
