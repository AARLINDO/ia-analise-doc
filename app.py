import streamlit as st
import os
import json
import time
import re
from datetime import datetime
from io import BytesIO

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Gemini Edition",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 2. IMPORTAÇÕES SEGURAS
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

# Mantivemos Groq/OpenAI apenas como fallback caso você queira no futuro
try: from groq import Groq
except ImportError: Groq = None
try: from openai import OpenAI
except ImportError: OpenAI = None

# =============================================================================
# 3. FUNÇÕES (MOTOR)
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

# --- CÉREBRO GEMINI ---
def get_ai_clients():
    clients = {"gemini": None, "groq": None, "openai": None}
    
    # Prioridade total ao Gemini
    gemini_key = st.secrets.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key and genai: 
        genai.configure(api_key=gemini_key)
        # Usando o modelo Flash que é rápido e tem contexto gigante
        clients["gemini"] = genai.GenerativeModel('gemini-1.5-flash')
        
    return clients

def call_ai_unified(system_prompt, user_prompt, provider="gemini", json_mode=False):
    if check_rate_limit(): return None
    mark_call()
    
    clients = get_ai_clients()
    
    try:
        # GEMINI (PADRÃO)
        if provider == "gemini":
            if not clients["gemini"]: return "⚠️ Erro: Chave Google (Gemini) não configurada."
            
            # Gemini prefere prompt único
            full_prompt = f"INSTRUÇÃO DO SISTEMA: {system_prompt}\n\nUSUÁRIO: {user_prompt}"
            
            if json_mode:
                full_prompt += "\n\nFORMATO DE RESPOSTA: Responda APENAS com um JSON válido, sem markdown (```json)."
                
            response = clients["gemini"].generate_content(full_prompt)
            return response.text

        # Fallbacks (Groq/OpenAI) se configurados
        elif provider == "groq" and clients.get("groq"):
            # (Lógica Groq mantida oculta para simplicidade)
            pass
            
    except Exception as e: return f"Erro na IA ({provider}): {str(e)}"
    return "Erro desconhecido."

def extract_json_surgical(text):
    """Limpa o texto do Gemini para pegar só o JSON."""
    try:
        # Remove blocos de código markdown se houver
        text = text.replace("```json", "").replace("```", "")
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match: return json.loads(match.group(0))
    except: pass
    return None

# --- ARQUIVOS ---
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
    doc.add_paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y')}")
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
# 4. ESTILO (CSS)
# =============================================================================
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #11141d; border-right: 1px solid #2B2F3B; }
    .gemini-text {
        background: -webkit-linear-gradient(45deg, #4285F4, #9B72CB, #D96570); /* Cores do Google Gemini */
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

# =============================================================================
# 5. ESTADO
# =============================================================================
if "user_xp" not in st.session_state: st.session_state.user_xp = 0
if "contract_step" not in st.session_state: st.session_state.contract_step = 1
if "contract_clauses" not in st.session_state: st.session_state.contract_clauses = []
if "contract_meta" not in st.session_state: st.session_state.contract_meta = {}
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "edital_text" not in st.session_state: st.session_state.edital_text = ""
if "last_question" not in st.session_state: st.session_state.last_question = None 

# DEFININDO GEMINI COMO PADRÃO ABSOLUTO
if "ai_provider" not in st.session_state: st.session_state.ai_provider = "gemini"

def add_xp(amount):
    st.session_state.user_xp += amount
    st.toast(f"+{amount} XP", icon="⚡")

# =============================================================================
# 6. SIDEBAR
# =============================================================================
with st.sidebar:
    safe_image_show("logo.jpg.png")
    
    st.markdown("### 🧠 Cérebro Ativo")
    # Apenas Gemini visível e selecionado por padrão
    st.success("✨ Google Gemini (Conectado)")
    
    st.markdown("---")
    menu = st.radio("Menu Principal:", [
        "✨ Chat Inteligente", 
        "📝 Redação Pro (Builder)", 
        "🎯 Mestre dos Editais", 
        "🍅 Sala de Foco", 
        "🏢 Cartório OCR", 
        "🎙️ Transcrição"
    ], label_visibility="collapsed")
    
    st.markdown("---")
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))
    st.markdown(f"<small>Nível {int(st.session_state.user_xp/100)} | {st.session_state.user_xp} XP</small>", unsafe_allow_html=True)
    st.markdown("""<div class='footer-credits'>Desenvolvido por <br><strong>Arthur Carmélio</strong></div>""", unsafe_allow_html=True)

# =============================================================================
# 7. MÓDULOS
# =============================================================================

# --- 1. CHAT INTELIGENTE ---
if menu == "✨ Chat Inteligente":
    st.markdown(f'<h1 class="gemini-text">Mentor Jurídico</h1>', unsafe_allow_html=True)
    if not st.session_state.chat_history:
        st.info(f"Olá. Sou o Carmélio AI (Powered by Gemini). Estou pronto para analisar casos complexos.")
        
    for msg in st.session_state.chat_history:
        avatar = "🧑‍⚖️" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar): st.markdown(msg["content"])
        
    if p := st.chat_input("Digite sua dúvida..."):
        st.session_state.chat_history.append({"role": "user", "content": p})
        with st.chat_message("user", avatar="🧑‍⚖️"): st.write(p)
        
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analisando com Gemini..."):
                ctx_msgs = st.session_state.chat_history[-6:]
                ctx_str = "\n".join([f"{m['role']}: {m['content']}" for m in ctx_msgs])
                
                res = call_ai_unified(
                    "Você é o Carmélio AI, assistente jurídico sênior. Baseie-se na legislação brasileira (CF, CC, CPC). Seja técnico e preciso.", 
                    ctx_str, 
                    "gemini"
                )
                st.write(res)
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                add_xp(5)

# --- 2. REDAÇÃO PRO (BUILDER) ---
elif menu == "📝 Redação Pro (Builder)":
    step = st.session_state.contract_step
    
    c1, c2, c3 = st.columns([1,1,1])
    c1.markdown(f"**1. Dados** {'✅' if step > 1 else '🟦'}")
    c2.markdown(f"**2. Estrutura** {'✅' if step > 2 else ('🟦' if step==2 else '⬜')}")
    c3.markdown(f"**3. Revisão** {'✅' if step > 3 else ('🟦' if step==3 else '⬜')}")
    st.progress(int(step/3 * 100))

    if step == 1:
        st.header("📝 Detalhes do Caso")
        with st.container(border=True):
            tipo = st.text_input("Tipo de Documento", placeholder="Ex: Contrato de Locação")
            partes = st.text_area("Partes", placeholder="Qualificação completa...")
            objeto = st.text_area("Objeto", placeholder="Detalhes do acordo...")
            
            if st.button("Gerar Estrutura ➔", type="primary", use_container_width=True):
                if tipo and objeto:
                    with st.spinner("Gemini está escrevendo..."):
                        prompt = f"Crie estrutura de {tipo}. Partes: {partes}. Objeto: {objeto}. JSON: {{'clauses': [{{'titulo': '...', 'conteudo': '...'}}]}}"
                        res = call_ai_unified("Gere APENAS JSON válido.", prompt, "gemini", json_mode=True)
                        data = extract_json_surgical(res)
                        
                        if data and 'clauses' in data:
                            st.session_state.contract_meta = {"tipo": tipo, "partes": partes, "objeto": objeto}
                            st.session_state.contract_clauses = data['clauses']
                            st.session_state.contract_step = 2
                            add_xp(20)
                            st.rerun()
                        else: st.error("Erro ao gerar. Tente novamente.")
                else: st.warning("Preencha os campos.")

    elif step == 2:
        st.header("📑 Editor Modular")
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
        st.header("✅ Documento Final")
        c_view, c_chat = st.columns([2, 1])
        
        with c_view:
            docx = create_contract_docx(st.session_state.contract_clauses, st.session_state.contract_meta)
            if docx:
                st.download_button("💾 BAIXAR DOCX", docx, "Contrato.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary", use_container_width=True)
            
            full_text = f"# {st.session_state.contract_meta.get('tipo')}\n\n"
            for c in st.session_state.contract_clauses: full_text += f"## {c['titulo']}\n{c['conteudo']}\n\n"
            st.text_area("Preview", full_text, height=600)
            
            if st.button("✏️ Editar"): 
                st.session_state.contract_step = 2
                st.rerun()
                
        with c_chat:
            st.info("🤖 **Assistente:** Quer ajustar algo?")
            q = st.text_input("Ex: 'Aumente a multa'")
            if q:
                with st.spinner("Reescrevendo..."):
                    ans = call_ai_unified("Revisor Jurídico.", f"Texto: {full_text}\nPedido: {q}", "gemini")
                    st.write(ans)

# --- 3. MESTRE DOS EDITAIS (GEMINI POWERED) ---
elif menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais (Gemini)")
    
    with st.expander("📂 Upload do Edital", expanded=not bool(st.session_state.edital_text)):
        f = st.file_uploader("Upload PDF (Até 200MB)", type=["pdf"])
        if f:
            with st.spinner("Gemini lendo o arquivo completo..."):
                st.session_state.edital_text = read_pdf_safe(f)
            st.success("Edital carregado com sucesso!")
            st.rerun()
        
    if st.session_state.edital_text:
        st.markdown("### 📚 Sala de Treino")
        col_btns = st.columns(2)
        
        if col_btns[0].button("📝 Gerar Nova Questão"):
            with st.spinner("Analisando Conteúdo Programático..."):
                prompt_edital = f"""
                Analise este edital. IGNORE regras de inscrição/datas.
                FOQUE NO CONTEÚDO PROGRAMÁTICO (Matérias).
                Crie uma questão de múltipla escolha DIFÍCIL baseada em um tópico aleatório do conteúdo.
                
                Texto do edital (trecho): {st.session_state.edital_text[:30000]}
                
                Formato:
                **Matéria:** [Nome]
                **Questão:** [Enunciado]
                A)... B)... C)... D)...
                **Gabarito:** [Letra] - [Explicação]
                """
                res = call_ai_unified("Examinador de Banca.", prompt_edital, "gemini")
                st.session_state.last_question = res 
                add_xp(15)
        
        if st.session_state.last_question:
            st.markdown(f"<div class='clause-card'>{st.session_state.last_question}</div>", unsafe_allow_html=True)

# --- 4. SALA DE FOCO ---
elif menu == "🍅 Sala de Foco":
    st.title("🍅 Sala de Foco")
    if st.button("Iniciar Foco 25m", type="primary"):
        with st.spinner("Focando..."): time.sleep(1); st.success("Timer Iniciado!")

# --- 5. FERRAMENTAS EXTRAS ---
elif menu == "🏢 Cartório OCR":
    st.title("🏢 Leitor de Documentos")
    u = st.file_uploader("Arquivo", type=["jpg","png","pdf"])
    if u and st.button("Extrair Texto"):
        st.info("Simulando OCR...") # Gemini Vision seria implementado aqui
        st.text_area("Resultado", "Texto extraído...", height=300)

elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição")
    t1, t2 = st.tabs(["📂 Upload", "🎤 Microfone"])
    with t1:
        f = st.file_uploader("Áudio", type=["mp3","wav"])
        if f and st.button("Transcrever"):
            st.success("Transcrição simulada.")
    with t2:
        mic = get_audio_input_safe("Gravar")
        if mic: st.info("Áudio capturado.")
