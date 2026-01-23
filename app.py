import streamlit as st
import streamlit.components.v1 as components
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
    page_title="Carmélio AI | Pro Studio",
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
# 3. WIDGETS DE FOCO (SIDEBAR)
# =============================================================================
def render_sidebar_widgets():
    """
    Renderiza Timer + Spotify + Créditos na Sidebar.
    O Timer usa JavaScript para não travar o Python.
    """
    
    # --- 1. TIMER POMODORO (Com Alerta Sonoro) ---
    pomodoro_html = """
    <style>
        .timer-box {
            background-color: #1F2430; border: 1px solid #374151;
            border-radius: 8px; padding: 10px; text-align: center;
            color: white; font-family: sans-serif; margin-bottom: 10px;
        }
        .time-display {
            font-size: 28px; font-weight: bold; margin: 5px 0;
            color: #4285F4;
        }
        .btn-pomo {
            background: #2563EB; color: white; border: none;
            padding: 4px 8px; border-radius: 4px; cursor: pointer;
            margin: 2px; font-size: 11px; font-weight: bold;
        }
        .btn-stop { background: #DC2626; }
        .btn-pause { background: #D97706; }
        .presets { font-size: 10px; color: #aaa; margin-bottom: 5px; }
    </style>
    
    <div class="timer-box">
        <div style="font-size: 12px; font-weight: bold; color: #aaa;">🍅 Foco Ativo</div>
        <div class="time-display" id="timer">25:00</div>
        
        <div class="presets">
            <button class="btn-pomo" onclick="setTime(25)">25m</button>
            <button class="btn-pomo" onclick="setTime(50)">50m</button>
            <button class="btn-pomo" onclick="setTime(5)">5m</button>
        </div>

        <div>
            <button class="btn-pomo" onclick="startTimer()">▶ PLAY</button>
            <button class="btn-pomo btn-pause" onclick="pauseTimer()">⏸ PAUSE</button>
            <button class="btn-pomo btn-stop" onclick="resetTimer()">↻</button>
        </div>
    </div>

    <script>
        let time = 25 * 60;
        let initialTime = 25 * 60;
        let interval = null;
        let isRunning = false;
        // Som de Alerta (Beep)
        const alarm = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');

        function updateDisplay() {
            let m = Math.floor(time / 60);
            let s = time % 60;
            document.getElementById('timer').innerText = 
                (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
        }

        function setTime(mins) {
            pauseTimer();
            time = mins * 60;
            initialTime = time;
            updateDisplay();
        }

        function startTimer() {
            if (isRunning) return;
            isRunning = true;
            interval = setInterval(() => {
                if (time > 0) {
                    time--;
                    updateDisplay();
                } else {
                    clearInterval(interval);
                    isRunning = false;
                    document.getElementById('timer').innerText = "00:00";
                    alarm.play(); // Toca o som aqui!
                    alert("⏰ O Tempo Acabou!"); // Alerta visual também
                }
            }, 1000);
        }

        function pauseTimer() {
            clearInterval(interval);
            isRunning = false;
        }

        function resetTimer() {
            pauseTimer();
            time = initialTime;
            updateDisplay();
        }
    </script>
    """
    components.html(pomodoro_html, height=160)
    
    # --- 2. PLAYER DE MÚSICA (Spotify Embed) ---
    st.markdown("🎵 **Rádio Lofi**")
    # Iframe do Spotify compacto para caber na sidebar
    components.html(
        """<iframe style="border-radius:12px" src="https://open.spotify.com/embed/playlist/0vvXsWCC9xrXsKd4FyS8kM?utm_source=generator&theme=0" width="100%" height="80" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>""",
        height=85
    )

# =============================================================================
# 4. FUNÇÕES UTILITÁRIAS
# =============================================================================
def safe_image_show(image_path):
    if os.path.exists(image_path):
        try: st.image(image_path, use_container_width=True)
        except TypeError: st.image(image_path, use_column_width=True)
    else: st.markdown("## ⚖️ Carmélio AI")

def check_rate_limit():
    if "last_call" not in st.session_state: st.session_state.last_call = 0
    now = time.time()
    if now - st.session_state.last_call < 0.5: return True 
    return False

def mark_call(): st.session_state.last_call = time.time()

# =============================================================================
# 5. MOTOR DE IA
# =============================================================================
@st.cache_resource
def get_best_model():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key: return None, "⚠️ Configure secrets.toml"
    if not genai: return None, "⚠️ Biblioteca Google ausente"

    try:
        genai.configure(api_key=api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except:
            return None, "Erro de Chave API"

        pref = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-pro']
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
        full_prompt = f"SYS: {system_prompt}\nUSER: {user_prompt}"
        if json_mode: full_prompt += "\nOutput JSON only."
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

def read_pdf_safe(file_obj):
    if not pdfplumber: return "Erro: Biblioteca PDF ausente."
    try:
        text_content = ""
        with pdfplumber.open(BytesIO(file_obj.getvalue())) as pdf:
            max_pages = 60 
            for i, page in enumerate(pdf.pages):
                if i >= max_pages: break
                extracted = page.extract_text()
                if extracted: text_content += extracted + "\n"
        if not text_content.strip(): return None 
        return text_content
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
# 6. INTERFACE & CSS
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
    /* Estilo do Rodapé */
    .footer-credits { 
        text-align: center; margin-top: 30px; padding-top: 20px;
        border-top: 1px solid #2B2F3B; color: #6B7280; font-size: 11px; 
    }
    .footer-credits strong { color: #E0E0E0; }
</style>
""", unsafe_allow_html=True)

if "user_xp" not in st.session_state: st.session_state.user_xp = 0
if "contract_step" not in st.session_state: st.session_state.contract_step = 1
if "contract_clauses" not in st.session_state: st.session_state.contract_clauses = []
if "contract_meta" not in st.session_state: st.session_state.contract_meta = {}
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# Estados do Mestre
if "edital_text" not in st.session_state: st.session_state.edital_text = ""
if "edital_filename" not in st.session_state: st.session_state.edital_filename = "" 
if "quiz_data" not in st.session_state: st.session_state.quiz_data = None
if "quiz_show_answer" not in st.session_state: st.session_state.quiz_show_answer = False
if "user_choice" not in st.session_state: st.session_state.user_choice = None

def add_xp(amount):
    st.session_state.user_xp += amount
    st.toast(f"+{amount} XP | Nível {int(st.session_state.user_xp/100)}", icon="⚡")

# =============================================================================
# 7. SIDEBAR COMPLETA
# =============================================================================
with st.sidebar:
    safe_image_show("logo.jpg.png")
    
    # >>> WIDGETS: TIMER + MÚSICA <<<
    render_sidebar_widgets()
    st.markdown("---")
    
    # STATUS IA
    model_obj, status_msg = get_best_model()
    if not model_obj: st.error(f"❌ {status_msg}")
    else: st.success(f"🟢 **{status_msg}**")
        
    menu = st.radio("Navegação", [
        "✨ Chat Inteligente", 
        "📝 Gere seu Contrato", 
        "🎯 Mestre dos Editais", 
        "🏢 Cartório OCR", 
        "🎙️ Transcrição"
    ], label_visibility="collapsed")
    
    # BARRA DE XP
    st.markdown("---")
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))
    
    # >>> CRÉDITOS DO DESENVOLVEDOR <<<
    st.markdown("""
    <div class='footer-credits'>
        Desenvolvido por<br>
        <strong>Arthur Carmélio</strong><br>
        © 2024 Carmélio AI
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# 8. MÓDULOS PRINCIPAIS
# =============================================================================

# --- 1. CHAT ---
if menu == "✨ Chat Inteligente":
    st.markdown('<h1 class="gemini-text">Mentor Jurídico</h1>', unsafe_allow_html=True)
    if not st.session_state.chat_history: st.info(f"Olá. Sou o Carmélio AI.")
    for msg in st.session_state.chat_history:
        avatar = "🧑‍⚖️" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar): st.markdown(msg["content"])
    if p := st.chat_input("Dúvida..."):
        st.session_state.chat_history.append({"role": "user", "content": p})
        with st.chat_message("user", avatar="🧑‍⚖️"): st.write(p)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("..."):
                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history[-6:]])
                res = call_gemini("Advogado Sênior.", history)
                st.write(res)
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                add_xp(5)

# --- 2. CONTRATOS ---
elif menu == "📝 Gere seu Contrato":
    step = st.session_state.contract_step
    c1, c2, c3 = st.columns([1,1,1])
    c1.markdown(f"**1. Tipo** {'✅' if step > 1 else '🟦'}")
    c2.markdown(f"**2. Minuta** {'✅' if step > 2 else ('🟦' if step==2 else '⬜')}")
    c3.markdown(f"**3. Baixar** {'✅' if step > 3 else ('🟦' if step==3 else '⬜')}")
    st.progress(int(step/3 * 100))

    if step == 1:
        st.header("📝 Qual contrato?")
        with st.container(border=True):
            tipo_contrato = st.selectbox("Modelo:", ["Prestação de Serviços", "Locação de Imóvel", "Compra e Venda Imóvel", "Compra e Venda Veículo", "Outro"])
            partes = st.text_area("Partes")
            objeto = st.text_area("Objeto")
            if st.button("Gerar Minuta ➔", type="primary", use_container_width=True):
                if partes and objeto:
                    with st.spinner("Gerando..."):
                        lei = "Lei do Inquilinato" if "Locação" in tipo_contrato else "Código Civil"
                        prompt = f"Crie contrato de {tipo_contrato}. Base: {lei}. Partes: {partes}. Objeto: {objeto}. JSON: {{'clauses': [{{'titulo': '...', 'conteudo': '...'}}]}}"
                        res = call_gemini("JSON only.", prompt, json_mode=True)
                        data = extract_json_surgical(res)
                        if data and 'clauses' in data:
                            st.session_state.contract_meta = {"tipo": tipo_contrato, "partes": partes, "objeto": objeto}
                            st.session_state.contract_clauses = data['clauses']
                            st.session_state.contract_step = 2
                            add_xp(25)
                            st.rerun()
                        else: st.error("Erro.")
    elif step == 2:
        st.header("📑 Revisão"); 
        if st.button("➕ Cláusula"): st.session_state.contract_clauses.append({"titulo":"Nova","conteudo":"..."}); st.rerun()
        to_remove = []
        for i, c in enumerate(st.session_state.contract_clauses):
            with st.expander(f"{i+1}. {c.get('titulo')}", expanded=False):
                nt = st.text_input("T",c['titulo'],key=f"t{i}"); nc = st.text_area("C",c['conteudo'],key=f"c{i}")
                st.session_state.contract_clauses[i] = {"titulo":nt,"conteudo":nc}
                if st.button("🗑️",key=f"d{i}"): to_remove.append(i)
        if to_remove:
            for i in sorted(to_remove, reverse=True): del st.session_state.contract_clauses[i]
            st.rerun()
        c1,c2=st.columns([1,2])
        if c1.button("⬅️"): st.session_state.contract_step=1; st.rerun()
        if c2.button("Finalizar ➔",type="primary",use_container_width=True): st.session_state.contract_step=3; st.rerun()
    elif step == 3:
        st.header("✅ Pronto")
        docx = create_contract_docx(st.session_state.contract_clauses, st.session_state.contract_meta)
        if docx: st.download_button("💾 Baixar", docx, "Contrato.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary", use_container_width=True)
        if st.button("✏️ Editar"): st.session_state.contract_step=2; st.rerun()

# --- 3. MESTRE DOS EDITAIS ---
elif menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais")
    
    # ONBOARDING (Explicação inicial)
    if not st.session_state.edital_text:
        st.markdown("""
        ### 🚀 Seu Professor Particular de Concursos
        Bem-vindo ao **Mestre dos Editais**.
        
        **Como usar:**
        1. Faça upload do seu Edital PDF.
        2. A IA lê o conteúdo programático.
        3. Você responde questões e treina para a prova!
        """)
        
    def gerar_turbo(dificuldade, foco):
        st.session_state.quiz_data = None
        st.session_state.quiz_show_answer = False
        st.session_state.user_choice = None
        with st.spinner(f"⚡ Gerando questão rápida ({dificuldade})..."):
            tema = f"FOCO: {foco}." if foco else "Tema aleatório do CONTEÚDO."
            texto_reduzido = st.session_state.edital_text[:15000]
            prompt = f"""
            Role: Banca Examinadora. Task: Criar questão técnica baseada no edital.
            IGNORE: Datas, regras admin. USE: Conteúdo Programático/Leis.
            {tema} Nível: {dificuldade}.
            JSON Output: {{"materia": "...", "enunciado": "...", "alternativas": {{"A":"...","B":"...","C":"...","D":"..."}}, "correta": "A", "explicacao": "..."}}
            """
            res = call_gemini("JSON Only.", f"{prompt}\nEDITAL:\n{texto_reduzido}", json_mode=True)
            data = extract_json_surgical(res)
            if data: st.session_state.quiz_data = data
            else: st.error("Erro rápido. Tente de novo.")

    if not st.session_state.edital_text:
        f = st.file_uploader("Carregar Edital (PDF)", type=["pdf"])
        if f and f.name != st.session_state.edital_filename:
            with st.spinner("Lendo..."):
                txt = read_pdf_safe(f)
                if txt: 
                    st.session_state.edital_text = txt
                    st.session_state.edital_filename = f.name
                    st.rerun()
                else: st.error("PDF sem texto.")
    else:
        c1, c2 = st.columns([3, 1])
        c1.success(f"📂 **{st.session_state.edital_filename}**")
        if c2.button("🗑️ Trocar", use_container_width=True): st.session_state.edital_text=""; st.rerun()
        
        st.markdown("---")
        cc, ca = st.columns([2, 1])
        with cc:
            diff = st.select_slider("Nível:", ["Fácil", "Médio", "Difícil", "Pesadelo"], value="Difícil")
            foco = st.text_input("Foco:", placeholder="Ex: Penal")
        with ca:
            st.write(""); st.write("")
            if st.button("🔥 GERAR", type="primary", use_container_width=True):
                gerar_turbo(diff, foco)
                st.rerun()

        if st.session_state.quiz_data:
            q = st.session_state.quiz_data
            st.markdown(f"### 📚 {q.get('materia','Geral')}")
            st.info(q['enunciado'])
            
            opts = q['alternativas']
            if not st.session_state.quiz_show_answer:
                c1,c2 = st.columns(2)
                if c1.button(f"A) {opts['A']}", use_container_width=True): st.session_state.user_choice="A"; st.session_state.quiz_show_answer=True; st.rerun()
                if c2.button(f"B) {opts['B']}", use_container_width=True): st.session_state.user_choice="B"; st.session_state.quiz_show_answer=True; st.rerun()
                if c1.button(f"C) {opts['C']}", use_container_width=True): st.session_state.user_choice="C"; st.session_state.quiz_show_answer=True; st.rerun()
                if c2.button(f"D) {opts['D']}", use_container_width=True): st.session_state.user_choice="D"; st.session_state.quiz_show_answer=True; st.rerun()
            else:
                u, c = st.session_state.user_choice, q['correta']
                for l,t in opts.items():
                    icon = "✅" if l==c else ("❌" if l==u else "⬜")
                    st.write(f"{icon} **{l})** {t}")
                
                if u==c: st.success("Acertou!"); add_xp(50)
                else: st.error(f"Errou. Correta: {c}")
                st.write(f"**Explicação:** {q['explicacao']}")
                
                if st.button("➡️ Próxima Rápida", type="primary"):
                    gerar_turbo(diff, foco)
                    st.rerun()

# --- 4. EXTRAS ---
elif menu == "🏢 Cartório OCR": st.title("🏢 OCR"); st.file_uploader("Arquivo")
elif menu == "🎙️ Transcrição": st.title("🎙️ Transcrição"); st.file_uploader("Áudio")
