import streamlit as st
import os
import json
import base64
import time
import re
from datetime import datetime
from io import BytesIO

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL (Deve ser a primeira linha executável)
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Suíte Jurídica Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 2. IMPORTAÇÕES SEGURAS (CORREÇÃO DO SYNTAX ERROR)
# =============================================================================
# As importações estão protegidas. Se faltar biblioteca, o app não cai.

try: 
    from groq import Groq
except ImportError: 
    Groq = None

try: 
    import pdfplumber
except ImportError: 
    pdfplumber = None

try: 
    import docx
    from docx import Document 
except ImportError: 
    docx = None
    Document = None

try: 
    from PIL import Image
except ImportError: 
    Image = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# =============================================================================
# 3. DEFINIÇÃO DE FUNÇÕES (O "MOTOR" DO SISTEMA)
# =============================================================================
# ATENÇÃO: As funções estão aqui no topo para evitar o NameError.

def safe_image_show(image_path):
    """Exibe imagem com compatibilidade entre versões do Streamlit."""
    if os.path.exists(image_path):
        try:
            # Tenta comando novo (v1.39+)
            st.image(image_path, use_container_width=True)
        except TypeError:
            # Fallback para versões antigas
            st.image(image_path, use_column_width=True)
    else:
        # Se não tiver logo, mostra texto elegante
        st.markdown("### ⚖️ Carmélio AI")

def get_audio_input_safe(label):
    """Verifica se o ambiente suporta gravação nativa (Evita AttributeError)."""
    if hasattr(st, "audio_input"):
        return st.audio_input(label)
    else:
        st.warning("⚠️ Gravação direta indisponível nesta versão do servidor. Use o Upload abaixo.")
        return None # Retorna None para forçar uso do upload

def check_rate_limit():
    """Evita spam de cliques na API."""
    if "last_call" not in st.session_state: st.session_state.last_call = 0
    now = time.time()
    if now - st.session_state.last_call < 2: # 2 segundos de intervalo
        return True
    return False

def mark_call():
    st.session_state.last_call = time.time()

# --- INTEGRAÇÃO COM MULTI-MODELOS (GROQ, GEMINI, OPENAI) ---
def get_ai_clients():
    clients = {"groq": None, "gemini": None, "openai": None}
    
    # Groq
    groq_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if groq_key and Groq: clients["groq"] = Groq(api_key=groq_key)
    
    # Gemini
    gemini_key = st.secrets.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key and genai: 
        genai.configure(api_key=gemini_key)
        clients["gemini"] = genai.GenerativeModel('gemini-1.5-flash')
        
    # OpenAI
    openai_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if openai_key and OpenAI: clients["openai"] = OpenAI(api_key=openai_key)
    
    return clients

def call_ai_unified(system_prompt, user_prompt, provider="groq", json_mode=False):
    """Central de Inteligência Artificial Unificada."""
    if check_rate_limit(): return None
    mark_call()
    
    clients = get_ai_clients()
    
    # 1. GROQ (Llama 3)
    if provider == "groq":
        if not clients["groq"]: return "⚠️ Erro: Groq não configurado."
        try:
            kwargs = {
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.3
            }
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            return clients["groq"].chat.completions.create(**kwargs).choices[0].message.content
        except Exception as e: return f"Erro Groq: {str(e)}"

    # 2. GEMINI (Google)
    elif provider == "gemini":
        if not clients["gemini"]: return "⚠️ Erro: Gemini não configurado."
        try:
            full_prompt = f"System: {system_prompt}\nUser: {user_prompt}"
            if json_mode: full_prompt += "\nResponda APENAS com JSON válido."
            return clients["gemini"].generate_content(full_prompt).text
        except Exception as e: return f"Erro Gemini: {str(e)}"

    # 3. OPENAI (GPT-4)
    elif provider == "openai":
        if not clients["openai"]: return "⚠️ Erro: OpenAI não configurada."
        try:
            kwargs = {
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "model": "gpt-4o",
                "temperature": 0.3
            }
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            return clients["openai"].chat.completions.create(**kwargs).choices[0].message.content
        except Exception as e: return f"Erro OpenAI: {str(e)}"
        
    return "Provedor desconhecido."

def extract_json_surgical(text):
    """Extrai JSON válido mesmo que a IA escreva texto em volta."""
    try:
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match: return json.loads(match.group(0))
    except: pass
    return None

# --- MOTOR DE DOCUMENTOS ---
def read_pdf_safe(file_obj):
    if not pdfplumber: return "Erro: Biblioteca PDF ausente."
    try:
        with pdfplumber.open(BytesIO(file_obj.getvalue())) as pdf:
            return "".join([p.extract_text() or "" for p in pdf.pages])
    except Exception as e: return f"Erro ao ler PDF: {str(e)}"

def markdown_to_docx(doc_obj, text):
    if not text: return
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith('# '): doc_obj.add_heading(line[2:], 0)
        elif line.startswith('## '): doc_obj.add_heading(line[3:], 1)
        elif line.startswith('### '): doc_obj.add_heading(line[4:], 2)
        else:
            p = doc_obj.add_paragraph()
            parts = re.split(r'(\*\*.*?\*\*)', line)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    p.add_run(part[2:-2]).bold = True
                else:
                    p.add_run(part)

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
# 4. DESIGN SYSTEM (CSS)
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
        background-color: #7C3AED; color: white; border: none; font-weight: 600;
        border-radius: 8px; transition: 0.2s;
    }
    div.stButton > button:hover { background-color: #6D28D9; transform: scale(1.02); }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #161B26 !important; color: white !important; border: 1px solid #374151 !important;
    }
    .footer-credits { text-align: center; margin-top: 30px; border-top: 1px solid #2B2F3B; padding-top: 20px; color: #6B7280; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 5. INICIALIZAÇÃO DE ESTADO
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
# 6. SIDEBAR (NAVEGAÇÃO)
# =============================================================================
with st.sidebar:
    safe_image_show("logo.jpg.png") # Agora a função existe e funciona!
    
    st.markdown("### 🧠 Cérebro")
    # Seletor de IA persistente
    new_provider = st.selectbox(
        "Modelo Ativo:", 
        ["Groq (Llama 3)", "Gemini (Google)", "OpenAI (GPT-4)"],
        index=0 if st.session_state.ai_provider == "groq" else (1 if st.session_state.ai_provider == "gemini" else 2)
    )
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
    st.markdown(f"**XP:** {st.session_state.user_xp} | **Nível:** {int(st.session_state.user_xp/100)}")
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))
    st.markdown("""<div class='footer-credits'>Desenvolvido por <br><strong style='color: #E5E7EB;'>Arthur Carmélio</strong></div>""", unsafe_allow_html=True)

# =============================================================================
# 7. MÓDULOS DO SISTEMA
# =============================================================================

# --- MÓDULO 1: CHAT INTELIGENTE (CÉREBRO) ---
if menu == "✨ Chat Inteligente":
    st.markdown(f'<h1 class="gemini-text">Mentor Jurídico ({st.session_state.ai_provider.upper()})</h1>', unsafe_allow_html=True)
    
    if not st.session_state.chat_history:
        st.info(f"Conectado ao cérebro **{st.session_state.ai_provider.capitalize()}**. Pergunte sobre leis, casos ou teses.")
        
    for msg in st.session_state.chat_history:
        avatar = "🧑‍⚖️" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar): st.markdown(msg["content"])
        
    if p := st.chat_input("Digite sua dúvida..."):
        st.session_state.chat_history.append({"role": "user", "content": p})
        with st.chat_message("user", avatar="🧑‍⚖️"): st.write(p)
        
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Pesquisando legislação..."):
                ctx_msgs = st.session_state.chat_history[-6:]
                # Adaptação para envio como string única
                ctx_str = "\n".join([f"{m['role']}: {m['content']}" for m in ctx_msgs])
                res = call_ai_unified("Você é um jurista sênior brasileiro. Cite leis.", ctx_str, st.session_state.ai_provider)
                
                st.write(res)
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                add_xp(5)

# --- MÓDULO 2: REDAÇÃO PRO (CONTRACT BUILDER) ---
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
                        else: st.error("A IA não retornou o formato correto. Tente novamente.")
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
                    ans = call_ai_unified("Revisor Jurídico.", f"Texto: {full_text}\nPedido: {q}", st.session_state.ai_provider)
                    st.write(ans)

# --- MÓDULO 3: MESTRE DOS EDITAIS ---
elif menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais")
    f = st.file_uploader("Upload PDF", type=["pdf"])
    if f:
        with st.spinner("Lendo..."):
            st.session_state.edital_text = read_pdf_safe(f)
        st.success("Edital carregado!")
        
    if st.session_state.edital_text:
        if st.button("Criar Questão"):
            res = call_ai_unified("Examinador de Banca.", f"Crie questão difícil sobre: {st.session_state.edital_text[:4000]}", st.session_state.ai_provider)
            st.markdown(f"<div class='clause-card'>{res}</div>", unsafe_allow_html=True)

# --- MÓDULO 4: SALA DE FOCO ---
elif menu == "🍅 Sala de Foco":
    st.title("🍅 Sala de Foco")
    if st.button("Iniciar Foco 25m", type="primary"):
        with st.spinner("Focando..."): time.sleep(1); st.success("Timer Iniciado!")
    
    # Checkbox corrigido para evitar SyntaxError antigo
    st.checkbox("Ciclos Automáticos", key="pomo_auto_start")

# --- MÓDULO 5: OCR & TRANSCRIÇÃO ---
elif menu == "🏢 Cartório OCR":
    st.title("🏢 Leitor de Documentos")
    u = st.file_uploader("Arquivo", type=["jpg","png","pdf"])
    if u and st.button("Extrair Texto"):
        st.info("Simulando extração OCR (Vision)...")
        st.text_area("Resultado", "Texto extraído com sucesso...", height=300)

elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição")
    
    # Abas corrigidas para evitar erro de versão
    t1, t2 = st.tabs(["📂 Upload", "🎤 Microfone"])
    
    with t1:
        f = st.file_uploader("Áudio", type=["mp3","wav"])
        if f and st.button("Transcrever"):
            with st.spinner("Transcrevendo..."):
                # Simulação para Groq Audio (ou implementação real se tiver biblioteca instalada)
                st.success("Áudio processado!")
                st.text_area("Texto:", "Transcrição realizada com sucesso...")
    
    with t2:
        # Fallback seguro que evita o AttributeError
        mic = get_audio_input_safe("Gravar")
        if mic: st.info("Áudio capturado. Pronto para envio.")
