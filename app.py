import streamlit as st
import os
import json
import time
import re
from datetime import datetime
from io import BytesIO

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL (PRIMEIRA LINHA OBRIGATÓRIA)
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Suíte Jurídica",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 2. IMPORTAÇÕES SEGURAS (BLINDAGEM CONTRA ERROS)
# =============================================================================
try: from groq import Groq
except ImportError: Groq = None

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

try: import google.generativeai as genai
except ImportError: genai = None

try: from openai import OpenAI
except ImportError: OpenAI = None

# =============================================================================
# 3. DEFINIÇÃO DE FUNÇÕES (MOTOR DO SISTEMA)
# =============================================================================
# As funções ficam AQUI EM CIMA para evitar o erro "NameError"

def safe_image_show(image_path):
    """Mostra a logo sem quebrar em versões diferentes do Streamlit."""
    if os.path.exists(image_path):
        try:
            st.image(image_path, use_container_width=True)
        except TypeError:
            st.image(image_path, use_column_width=True)
    else:
        st.markdown("## ⚖️ Carmélio AI")

def get_audio_input_safe(label):
    """Verifica se dá pra gravar áudio. Se não der, avisa e pede upload."""
    if hasattr(st, "audio_input"):
        return st.audio_input(label)
    else:
        st.warning("⚠️ Seu sistema não suporta gravação direta. Use a aba de Upload.")
        return None

def check_rate_limit():
    """Evita que o usuário clique rápido demais e trave a API."""
    if "last_call" not in st.session_state: st.session_state.last_call = 0
    now = time.time()
    if now - st.session_state.last_call < 1.5: 
        return True
    return False

def mark_call():
    st.session_state.last_call = time.time()

# --- CÉREBRO DE IA ---
def get_ai_clients():
    clients = {"groq": None, "gemini": None, "openai": None}
    
    # Tenta pegar chaves do secrets ou ambiente
    groq_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if groq_key and Groq: clients["groq"] = Groq(api_key=groq_key)
    
    gemini_key = st.secrets.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key and genai: 
        genai.configure(api_key=gemini_key)
        clients["gemini"] = genai.GenerativeModel('gemini-1.5-flash')
        
    openai_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if openai_key and OpenAI: clients["openai"] = OpenAI(api_key=openai_key)
    
    return clients

def call_ai_unified(system_prompt, user_prompt, provider="groq", json_mode=False):
    """Função única que chama a IA correta."""
    if check_rate_limit(): return None
    mark_call()
    
    clients = get_ai_clients()
    
    try:
        # 1. GROQ
        if provider == "groq":
            if not clients["groq"]: return "⚠️ Erro: Groq não configurado."
            kwargs = {
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.3
            }
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            return clients["groq"].chat.completions.create(**kwargs).choices[0].message.content

        # 2. GEMINI
        elif provider == "gemini":
            if not clients["gemini"]: return "⚠️ Erro: Gemini não configurado."
            full_prompt = f"System: {system_prompt}\nUser: {user_prompt}"
            if json_mode: full_prompt += "\nResponda APENAS com JSON válido."
            return clients["gemini"].generate_content(full_prompt).text

        # 3. OPENAI
        elif provider == "openai":
            if not clients["openai"]: return "⚠️ Erro: OpenAI não configurada."
            kwargs = {
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "model": "gpt-4o",
                "temperature": 0.3
            }
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            return clients["openai"].chat.completions.create(**kwargs).choices[0].message.content
            
    except Exception as e: return f"Erro na IA ({provider}): {str(e)}"
    return "Provedor desconhecido."

def extract_json_surgical(text):
    """Garante que pegamos o JSON mesmo se a IA falar antes."""
    try:
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match: return json.loads(match.group(0))
    except: pass
    return None

# --- PROCESSAMENTO DE ARQUIVOS ---
def read_pdf_safe(file_obj):
    if not pdfplumber: return "Erro: Biblioteca PDF ausente."
    try:
        with pdfplumber.open(BytesIO(file_obj.getvalue())) as pdf:
            return "".join([p.extract_text() or "" for p in pdf.pages])
    except Exception as e: return f"Erro PDF: {str(e)}"

def markdown_to_docx(doc_obj, text):
    """Converte formatação básica para Word."""
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
    doc.add_heading("2. OBJETO", level=1)
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
        background: -webkit-linear-gradient(45deg, #3B82F6, #8B5CF6, #EC4899);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.2rem;
    }
    .clause-card {
        background-color: #1F2430; border: 1px solid #374151;
        border-radius: 12px; padding: 20px; margin-bottom: 15px;
    }
    div.stButton > button {
        background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 100%);
        color: white; border: none; font-weight: 600; border-radius: 8px;
    }
    div.stButton > button:hover { transform: scale(1.02); }
    .footer-credits { text-align: center; margin-top: 40px; color: #6B7280; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 5. ESTADO (MEMÓRIA DO APP)
# =============================================================================
if "user_xp" not in st.session_state: st.session_state.user_xp = 0
if "contract_step" not in st.session_state: st.session_state.contract_step = 1
if "contract_clauses" not in st.session_state: st.session_state.contract_clauses = []
if "contract_meta" not in st.session_state: st.session_state.contract_meta = {}
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "edital_text" not in st.session_state: st.session_state.edital_text = ""
if "ai_provider" not in st.session_state: st.session_state.ai_provider = "groq"
if "pomo_auto_start" not in st.session_state: st.session_state.pomo_auto_start = False

def add_xp(amount):
    st.session_state.user_xp += amount
    st.toast(f"+{amount} XP | Nível {int(st.session_state.user_xp/100)}", icon="⚡")

# =============================================================================
# 6. SIDEBAR
# =============================================================================
with st.sidebar:
    safe_image_show("logo.jpg.png")
    
    st.markdown("### 🧠 Cérebro")
    prov_idx = 0 if st.session_state.ai_provider == "groq" else (1 if st.session_state.ai_provider == "gemini" else 2)
    new_provider = st.selectbox("Modelo:", ["Groq (Llama 3)", "Gemini (Google)", "OpenAI (GPT-4)"], index=prov_idx)
    
    if "Groq" in new_provider: st.session_state.ai_provider = "groq"
    elif "Gemini" in new_provider: st.session_state.ai_provider = "gemini"
    else: st.session_state.ai_provider = "openai"
    
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
        st.info(f"Conectado ao cérebro **{st.session_state.ai_provider.capitalize()}**. Pergunte sobre leis, casos ou teses.")
        
    for msg in st.session_state.chat_history:
        avatar = "🧑‍⚖️" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar): st.markdown(msg["content"])
        
    if p := st.chat_input("Dúvida jurídica..."):
        st.session_state.chat_history.append({"role": "user", "content": p})
        with st.chat_message("user", avatar="🧑‍⚖️"): st.write(p)
        
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Pesquisando..."):
                ctx_msgs = st.session_state.chat_history[-6:]
                # Converte para string para garantir compatibilidade com todos os modelos
                ctx_str = "\n".join([f"{m['role']}: {m['content']}" for m in ctx_msgs])
                
                res = call_ai_unified(
                    "Você é o Carmélio AI, um jurista sênior brasileiro. Cite leis (CF/88, CC, CPC) e seja didático.", 
                    ctx_str, 
                    st.session_state.ai_provider
                )
                st.write(res)
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                add_xp(5)

# --- 2. REDAÇÃO PRO (BUILDER) ---
elif menu == "📝 Redação Pro (Builder)":
    step = st.session_state.contract_step
    
    # Progresso Visual
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
                    with st.spinner("Arquitetando contrato..."):
                        prompt = f"Crie estrutura de {tipo}. Partes: {partes}. Objeto: {objeto}. JSON: {{'clauses': [{{'titulo': '...', 'conteudo': '...'}}]}}"
                        res = call_ai_unified("Gere APENAS JSON válido.", prompt, st.session_state.ai_provider, json_mode=True)
                        data = extract_json_surgical(res)
                        
                        if data and 'clauses' in data:
                            st.session_state.contract_meta = {"tipo": tipo, "partes": partes, "objeto": objeto}
                            st.session_state.contract_clauses = data['clauses']
                            st.session_state.contract_step = 2
                            add_xp(20)
                            st.rerun()
                        else: st.error("Erro na IA. Tente novamente.")
                else: st.warning("Preencha os campos.")

    elif step == 2:
        st.header("📑 Editor Modular")
        if st.button("➕ Nova Cláusula"):
            st.session_state.contract_clauses.append({"titulo": "Nova", "conteudo": "..."})
            st.rerun()

        to_remove = []
        for i, c in enumerate(st.session_state.contract_clauses):
            with st.expander(f"{i+1}. {c.get('titulo')}", expanded=False):
                new_t = st.
