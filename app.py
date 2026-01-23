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
    page_title="Carmélio AI | Contract Specialist",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 2. IMPORTAÇÕES
# =============================================================================
try: 
    import google.generativeai as genai
    LIB_VERSION = getattr(genai, "__version__", "Desconhecida")
except ImportError: 
    genai = None
    LIB_VERSION = "N/A"

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

def check_rate_limit():
    if "last_call" not in st.session_state: st.session_state.last_call = 0
    now = time.time()
    if now - st.session_state.last_call < 1.0: return True
    return False

def mark_call(): st.session_state.last_call = time.time()

# =============================================================================
# 4. MOTOR DE IA (AUTO-DETECTOR)
# =============================================================================
@st.cache_resource
def get_best_model():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key: return None, "⚠️ Configure o secrets.toml"
    if not genai: return None, "⚠️ Biblioteca Google ausente"

    try:
        genai.configure(api_key=api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except:
            return None, "Erro de Chave API"

        # Prioridade de Modelos
        pref = ['models/gemini-1.5-flash', 'models/gemini-pro']
        escolhido = next((m for m in pref if m in models), models[0] if models else None)
        
        if escolhido:
            return genai.GenerativeModel(escolhido.replace("models/", "")), escolhido.replace("models/", "")
            
        return None, "Nenhum modelo compatível."

    except Exception as e:
        return None, f"Erro Fatal: {str(e)}"

def call_gemini(system_prompt, user_prompt, json_mode=False):
    if check_rate_limit(): return None
    mark_call()
    
    model, model_name = get_best_model()
    if not model: return f"Erro de Conexão: {model_name}"
    
    try:
        full_prompt = f"SISTEMA (Role: {system_prompt})\n\nUSUÁRIO: {user_prompt}"
        if json_mode: full_prompt += "\n\nIMPORTANTE: Responda APENAS JSON válido."
            
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Erro na IA ({model_name}): {str(e)}"

def extract_json_surgical(text):
    try:
        text = text.replace("```json", "").replace("```", "")
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match: return json.loads(match.group(0))
    except: pass
    return None

# =============================================================================
# 5. ARQUIVOS
# =============================================================================
def read_pdf_safe(file_obj):
    if not pdfplumber: return "Erro PDF ausente."
    try:
        with pdfplumber.open(BytesIO(file_obj.getvalue())) as pdf:
            return "".join([p.extract_text() or "" for p in pdf.pages])
    except: return "Erro ao ler PDF."

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
# 6. UI
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

if "user_xp" not in st.session_state: st.session_state.user_xp = 0
if "contract_step" not in st.session_state: st.session_state.contract_step = 1
if "contract_clauses" not in st.session_state: st.session_state.contract_clauses = []
if "contract_meta" not in st.session_state: st.session_state.contract_meta = {}
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "edital_text" not in st.session_state: st.session_state.edital_text = ""
if "last_question" not in st.session_state: st.session_state.last_question = None 

def add_xp(amount):
    st.session_state.user_xp += amount
    st.toast(f"+{amount} XP", icon="⚡")

# =============================================================================
# 7. APP PRINCIPAL
# =============================================================================
with st.sidebar:
    safe_image_show("logo.jpg.png")
    model_obj, status_msg = get_best_model()
    if not model_obj: st.error(f"❌ {status_msg}")
    else: st.success(f"🟢 **{status_msg}**")
        
    st.markdown("---")
    # MENU ATUALIZADO AQUI
    menu = st.radio("Menu", [
        "✨ Chat Inteligente", 
        "📝 Gere seu Contrato",  # Renomeado
        "🎯 Mestre dos Editais", 
        "🍅 Sala de Foco", 
        "🏢 Cartório OCR", 
        "🎙️ Transcrição"
    ], label_visibility="collapsed")
    
    st.markdown("---")
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))
    st.markdown("""<div class='footer-credits'>Arthur Carmélio</div>""", unsafe_allow_html=True)

# --- 1. CHAT ---
if menu == "✨ Chat Inteligente":
    st.markdown('<h1 class="gemini-text">Mentor Jurídico</h1>', unsafe_allow_html=True)
    if not st.session_state.chat_history: st.info(f"Olá. Estou conectado.")
        
    for msg in st.session_state.chat_history:
        avatar = "🧑‍⚖️" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar): st.markdown(msg["content"])
        
    if p := st.chat_input("Dúvida jurídica..."):
        st.session_state.chat_history.append({"role": "user", "content": p})
        with st.chat_message("user", avatar="🧑‍⚖️"): st.write(p)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analisando..."):
                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history[-6:]])
                res = call_gemini("Você é um Advogado Sênior. Seja didático.", history)
                st.write(res)
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                add_xp(5)

# --- 2. GERE SEU CONTRATO (MÓDULO NOVO) ---
elif menu == "📝 Gere seu Contrato":
    step = st.session_state.contract_step
    
    c1, c2, c3 = st.columns([1,1,1])
    c1.markdown(f"**1. Tipo** {'✅' if step > 1 else '🟦'}")
    c2.markdown(f"**2. Minuta** {'✅' if step > 2 else ('🟦' if step==2 else '⬜')}")
    c3.markdown(f"**3. Baixar** {'✅' if step > 3 else ('🟦' if step==3 else '⬜')}")
    st.progress(int(step/3 * 100))

    if step == 1:
        st.header("📝 Qual contrato vamos criar?")
        with st.container(border=True):
            # SELETOR INTELIGENTE
            tipo_contrato = st.selectbox("Selecione o Modelo:", [
                "Prestação de Serviços",
                "Locação de Imóvel (Residencial/Comercial)",
                "Compra e Venda de Imóvel (Casa/Terreno)",
                "Compra e Venda de Veículo",
                "Outro (Personalizado)"
            ])
            
            st.info(f"💡 A IA usará a legislação específica para **{tipo_contrato}**.")
            
            partes = st.text_area("Quem são as Partes?", placeholder="Ex: Contratante: João Silva (CPF...); Contratado: Empresa X...")
            objeto = st.text_area("Detalhes do Negócio (Objeto)", placeholder="Ex: Venda de um Fiat Uno 2010... ou Aluguel da casa na Rua X...")
            
            if st.button("Gerar Minuta Jurídica ➔", type="primary", use_container_width=True):
                if partes and objeto:
                    with st.spinner(f"Consultando legislação para {tipo_contrato}..."):
                        
                        # PROMPT ESPECIALIZADO POR TIPO
                        lei_base = "Código Civil"
                        if "Locação" in tipo_contrato: lei_base = "Lei do Inquilinato (Lei 8.245/91)"
                        if "Consumidor" in tipo_contrato: lei_base = "CDC"
                        
                        prompt = f"""
                        Atue como Especialista em Contratos.
                        Crie uma minuta profissional de: {tipo_contrato}.
                        Base legal principal: {lei_base}.
                        
                        Partes: {partes}
                        Objeto/Detalhes: {objeto}
                        
                        REGRAS:
                        1. Crie cláusulas robustas de proteção.
                        2. Se for Veículo, inclua isenção de multas anteriores.
                        3. Se for Imóvel, cite matrícula e registro.
                        4. Retorne APENAS JSON no formato: {{'clauses': [{{'titulo': '...', 'conteudo': '...'}}]}}
                        """
                        
                        res = call_gemini("Gere APENAS JSON válido.", prompt, json_mode=True)
                        data = extract_json_surgical(res)
                        
                        if data and 'clauses' in data:
                            st.session_state.contract_meta = {"tipo": tipo_contrato, "partes": partes, "objeto": objeto}
                            st.session_state.contract_clauses = data['clauses']
                            st.session_state.contract_step = 2
                            add_xp(25)
                            st.rerun()
                        else: st.error("A IA falhou em gerar o JSON. Tente simplificar os detalhes.")
                else: st.warning("Preencha as partes e o objeto.")

    elif step == 2:
        st.header("📑 Revisão das Cláusulas")
        if st.button("➕ Adicionar Cláusula Manual"):
            st.session_state.contract_clauses.append({"titulo": "Nova Cláusula", "conteudo": "Escreva aqui..."})
            st.rerun()

        to_remove = []
        for i, c in enumerate(st.session_state.contract_clauses):
            with st.expander(f"{i+1}. {c.get('titulo')}", expanded=False):
                new_t = st.text_input(f"Título", c.get('titulo'), key=f"t_{i}") 
                new_c = st.text_area(f"Texto", c.get('conteudo'), height=200, key=f"c_{i}")
                st.session_state.contract_clauses[i] = {"titulo": new_t, "conteudo": new_c}
                if st.button("🗑️ Remover", key=f"d_{i}"): to_remove.append(i)
        
        if to_remove:
            for i in sorted(to_remove, reverse=True): del st.session_state.contract_clauses[i]
            st.rerun()

        c1, c2 = st.columns([1, 2])
        if c1.button("⬅️ Voltar"): 
            st.session_state.contract_step = 1
            st.rerun()
        if c2.button("Finalizar e Baixar ➔", type="primary", use_container_width=True):
            st.session_state.contract_step = 3
            st.rerun()

    elif step == 3:
        st.header("✅ Seu Contrato está Pronto!")
        c_view, c_chat = st.columns([2, 1])
        with c_view:
            docx = create_contract_docx(st.session_state.contract_clauses, st.session_state.contract_meta)
            if docx:
                st.download_button("💾 BAIXAR CONTRATO (.docx)", docx, "Contrato_CarmelioAI.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary", use_container_width=True)
            
            full_text = f"# {st.session_state.contract_meta.get('tipo')}\n\n"
            for c in st.session_state.contract_clauses: full_text += f"## {c['titulo']}\n{c['conteudo']}\n\n"
            st.text_area("Pré-visualização", full_text, height=600)
            
            if st.button("✏️ Continuar Editando"): 
                st.session_state.contract_step = 2
                st.rerun()
        with c_chat:
            st.info("🤖 **IA:** Quer melhorar alguma cláusula específica?")
            q = st.text_input("Ex: 'Deixe a multa mais rígida'")
            if q:
                with st.spinner("Reescrevendo..."):
                    ans = call_gemini("Revisor de Contratos.", f"Texto atual: {full_text}\nPedido: {q}")
                    st.write(ans)

# --- 3. EDITAIS ---
elif menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais")
    f = st.file_uploader("Upload PDF", type=["pdf"])
    if f:
        with st.spinner("Lendo..."): st.session_state.edital_text = read_pdf_safe(f)
        st.success("Lido!")
    
    if st.session_state.edital_text:
        if st.button("📝 Criar Questão"):
            with st.spinner("Gerando..."):
                st.session_state.last_question = call_gemini("Examinador.", f"Crie questão difícil sobre: {st.session_state.edital_text[:30000]}")
        if st.session_state.last_question:
            st.markdown(f"<div class='clause-card'>{st.session_state.last_question}</div>", unsafe_allow_html=True)

# --- 4. SALA DE FOCO (FUNCIONAL) ---
elif menu == "🍅 Sala de Foco":
    st.title("🍅 Sala de Foco")
    c_timer, c_music = st.columns(2)
    with c_timer:
        st.subheader("⏱️ Pomodoro")
        tempo = st.number_input("Minutos", 1, 120, 25)
        if st.button("▶️ Iniciar"):
            bar = st.progress(0); status = st.empty()
            total = tempo * 60
            for i in range(total):
                time.sleep(1) # Simulação visual (em app real usaria async)
                rest = total - (i+1)
                status.markdown(f"### {rest//60:02d}:{rest%60:02d}")
                bar.progress((i+1)/total)
            st.success("Fim do ciclo!")
    with c_music:
        st.subheader("🎵 Lofi Radio")
        st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")

# --- 5. EXTRAS ---
elif menu == "🏢 Cartório OCR":
    st.title("🏢 OCR"); st.file_uploader("Arquivo")

elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição"); st.file_uploader("Áudio")
