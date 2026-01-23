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
    page_title="Carmélio AI | Ultimate Studio",
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
# 3. WIDGETS DA BARRA LATERAL (TIMER + PLAYER)
# =============================================================================
def render_sidebar_widgets():
    sidebar_html = """
    <style>
        .widget-box {
            background-color: #1F2430; border: 1px solid #374151;
            border-radius: 12px; padding: 15px; text-align: center;
            color: white; font-family: sans-serif; margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .title { font-size: 12px; font-weight: bold; color: #8B949E; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
        .time-display { font-size: 36px; font-weight: 800; margin: 10px 0; color: #4285F4; text-shadow: 0 0 10px rgba(66, 133, 244, 0.3); }
        .btn { border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; margin: 3px; font-size: 12px; font-weight: 600; transition: all 0.2s; }
        .btn:hover { opacity: 0.9; transform: scale(1.05); }
        .btn-primary { background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; }
        .btn-danger { background: linear-gradient(135deg, #DC2626, #B91C1C); color: white; }
        .btn-warn { background: linear-gradient(135deg, #D97706, #B45309); color: white; }
        .btn-dark { background: #374151; color: #E5E7EB; border: 1px solid #4B5563; }
        .presets { margin-bottom: 10px; display: flex; justify-content: center; gap: 5px; }
        .preset-btn { background: transparent; border: 1px solid #4B5563; color: #9CA3AF; padding: 2px 8px; border-radius: 10px; font-size: 10px; cursor: pointer; }
        .preset-btn:hover { border-color: #60A5FA; color: #60A5FA; }
        .player-status { font-size: 11px; color: #34D399; margin-top: 5px; display: none; }
        iframe { display: none; }
    </style>
    
    <div class="widget-box">
        <div class="title">🍅 Pomodoro Focus</div>
        <div class="presets">
            <button class="preset-btn" onclick="setTime(25)">25m</button>
            <button class="preset-btn" onclick="setTime(50)">50m</button>
            <button class="preset-btn" onclick="setTime(5)">5m</button>
        </div>
        <div class="time-display" id="timer">25:00</div>
        <div id="pomo-status" style="font-size:11px; color:#6B7280; margin-bottom:10px;">Pronto</div>
        <div>
            <button class="btn btn-primary" onclick="startTimer()">▶ Iniciar</button>
            <button class="btn btn-warn" onclick="pauseTimer()">⏸ Pausa</button>
            <button class="btn btn-danger" onclick="resetTimer()">↺</button>
        </div>
    </div>

    <div class="widget-box">
        <div class="title">🎵 Rádio Lofi (24h)</div>
        <div id="youtube-player"></div>
        <div style="margin-top:10px;">
            <button class="btn btn-dark" onclick="playMusic()">▶ Play</button>
            <button class="btn btn-dark" onclick="pauseMusic()">⏸ Pause</button>
            <button class="btn btn-dark" onclick="volUp()">🔊 +</button>
            <button class="btn btn-dark" onclick="volDown()">🔉 -</button>
        </div>
        <div id="music-status" class="player-status">Tocando...</div>
    </div>

    <script>
        let time = 25 * 60; let initialTime = 25 * 60; let interval = null;
        const alarm = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');

        function updateDisplay() {
            let m = Math.floor(time / 60); let s = time % 60;
            document.getElementById('timer').innerText = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
        }
        function setTime(mins) {
            pauseTimer(); time = mins * 60; initialTime = time; updateDisplay();
            document.getElementById('pomo-status').innerText = mins + " min definido";
        }
        function startTimer() {
            if (interval) return;
            document.getElementById('pomo-status').innerText = "Focando...";
            interval = setInterval(() => {
                if (time > 0) { time--; updateDisplay(); } 
                else { clearInterval(interval); interval = null; document.getElementById('timer').innerText = "00:00"; alarm.play(); document.getElementById('pomo-status').innerText = "Acabou!"; }
            }, 1000);
        }
        function pauseTimer() { clearInterval(interval); interval = null; document.getElementById('pomo-status').innerText = "Pausado"; }
        function resetTimer() { pauseTimer(); time = initialTime; updateDisplay(); document.getElementById('pomo-status').innerText = "Reiniciado"; }

        var tag = document.createElement('script'); tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0]; firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
        var player;
        function onYouTubeIframeAPIReady() {
            player = new YT.Player('youtube-player', {
                height: '0', width: '0', videoId: 'jfKfPfyJRdk',
                playerVars: { 'playsinline': 1, 'controls': 0, 'loop': 1, 'playlist': 'jfKfPfyJRdk' }
            });
        }
        function playMusic() { if(player) { player.playVideo(); document.getElementById('music-status').style.display='block'; document.getElementById('music-status').innerText="Tocando 🎵"; } }
        function pauseMusic() { if(player) { player.pauseVideo(); document.getElementById('music-status').innerText="Pausado"; } }
        function volUp() { if(player) { player.setVolume(player.getVolume() + 10); } }
        function volDown() { if(player) { player.setVolume(player.getVolume() - 10); } }
    </script>
    """
    components.html(sidebar_html, height=350)

# =============================================================================
# 4. FUNÇÕES DE IA & ARQUIVOS
# =============================================================================
def safe_image_show(image_path):
    if os.path.exists(image_path):
        try: st.image(image_path, use_container_width=True)
        except TypeError: st.image(image_path, use_column_width=True)
    else: st.markdown("## ⚖️ Carmélio AI")

def check_rate_limit():
    if "last_call" not in st.session_state: st.session_state.last_call = 0
    if time.time() - st.session_state.last_call < 0.5: return True 
    return False

def mark_call(): st.session_state.last_call = time.time()

@st.cache_resource
def get_best_model():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key: return None, "⚠️ Configure secrets.toml"
    try:
        genai.configure(api_key=api_key)
        try: models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except: return None, "Erro de Chave API"
        pref = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-pro']
        escolhido = next((m for m in pref if m in models), models[0] if models else None)
        if escolhido: return genai.GenerativeModel(escolhido.replace("models/", "")), escolhido.replace("models/", "")
        return None, "Nenhum modelo compatível."
    except Exception as e: return None, f"Erro Fatal: {str(e)}"

def call_gemini(system_prompt, user_prompt, json_mode=False, image=None):
    if check_rate_limit(): return None
    mark_call()
    model, name = get_best_model()
    if not model: return f"Erro: {name}"
    try:
        if image:
            # Modo Visão (OCR)
            response = model.generate_content([system_prompt, image, user_prompt])
        else:
            # Modo Texto
            full_prompt = f"SYS: {system_prompt}\nUSER: {user_prompt}"
            if json_mode: full_prompt += "\nOutput JSON only."
            response = model.generate_content(full_prompt)
        return response.text
    except Exception as e: return f"Erro IA: {str(e)}"

def extract_json_surgical(text):
    try:
        text = text.replace("```json", "").replace("```", "")
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match: return json.loads(match.group(0))
    except: pass
    return None

def read_pdf_safe(file_obj):
    if not pdfplumber: return None
    try:
        text = ""
        with pdfplumber.open(BytesIO(file_obj.getvalue())) as pdf:
            for i, p in enumerate(pdf.pages):
                if i >= 60: break
                text += (p.extract_text() or "") + "\n"
        return text if text.strip() else None
    except: return None

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
        # Simples conversão de quebra de linha
        for line in clause.get('conteudo', '').split('\n'):
            if line.strip(): doc.add_paragraph(line.strip())
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# =============================================================================
# 6. ESTILO E ESTADO
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
    div.stButton > button {
        background: linear-gradient(90deg, #2563EB 0%, #7C3AED 100%);
        color: white; border: none; font-weight: 600; border-radius: 8px;
    }
    .footer-credits { 
        text-align: center; margin-top: 30px; padding-top: 20px;
        border-top: 1px solid #2B2F3B; color: #6B7280; font-size: 11px; 
    }
    .footer-credits strong { color: #E0E0E0; }
    .onboarding-box {
        background-color: #1F2430; padding: 20px; border-radius: 10px;
        border-left: 5px solid #4285F4; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

if "user_xp" not in st.session_state: st.session_state.user_xp = 0
if "contract_step" not in st.session_state: st.session_state.contract_step = 1
if "contract_clauses" not in st.session_state: st.session_state.contract_clauses = []
if "contract_meta" not in st.session_state: st.session_state.contract_meta = {}
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "edital_text" not in st.session_state: st.session_state.edital_text = ""
if "edital_filename" not in st.session_state: st.session_state.edital_filename = "" 
if "quiz_data" not in st.session_state: st.session_state.quiz_data = None
if "quiz_show_answer" not in st.session_state: st.session_state.quiz_show_answer = False
if "user_choice" not in st.session_state: st.session_state.user_choice = None

def add_xp(amount):
    st.session_state.user_xp += amount
    st.toast(f"+{amount} XP | Nível {int(st.session_state.user_xp/100)}", icon="⚡")

# =============================================================================
# 7. APP PRINCIPAL
# =============================================================================
with st.sidebar:
    safe_image_show("logo.jpg.png")
    
    render_sidebar_widgets() # TIMER + MÚSICA
    st.markdown("---")
    
    model_obj, status_msg = get_best_model()
    if not model_obj: st.error(f"❌ {status_msg}")
    else: st.success(f"🟢 **{status_msg}**")
        
    menu = st.radio("Menu", [
        "✨ Chat Inteligente", 
        "📝 Gere seu Contrato", 
        "🎯 Mestre dos Editais", 
        "🏢 Cartório OCR", 
        "🎙️ Transcrição"
    ], label_visibility="collapsed")
    
    st.markdown("---")
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))
    
    # RODAPÉ ATUALIZADO 2026
    st.markdown("""
    <div class='footer-credits'>
        Desenvolvido por<br>
        <strong>Arthur Carmélio</strong><br>
        © 2026 Carmélio AI
    </div>
    """, unsafe_allow_html=True)

# --- 1. CHAT ---
if menu == "✨ Chat Inteligente":
    st.markdown('<h1 class="gemini-text">Mentor Jurídico</h1>', unsafe_allow_html=True)
    if not st.session_state.chat_history: 
        st.markdown("""
        <div class="onboarding-box">
            <h4>👋 Olá, Arthur!</h4>
            <p>Sou seu <b>Mentor Jurídico</b> pessoal. Posso te ajudar com dúvidas de leis, 
            pesquisas de jurisprudência ou apenas conversar sobre seus estudos.</p>
        </div>
        """, unsafe_allow_html=True)
        
    for msg in st.session_state.chat_history:
        avatar = "🧑‍⚖️" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar): st.markdown(msg["content"])
    if p := st.chat_input("Digite sua dúvida..."):
        st.session_state.chat_history.append({"role": "user", "content": p})
        with st.chat_message("user", avatar="🧑‍⚖️"): st.write(p)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analisando..."):
                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history[-6:]])
                res = call_gemini("Advogado Sênior. Responda em Português do Brasil.", history)
                st.write(res)
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                add_xp(5)

# --- 2. CONTRATOS ---
elif menu == "📝 Gere seu Contrato":
    st.title("📝 Gere seu Contrato")
    step = st.session_state.contract_step
    
    if step == 1:
        st.markdown("""
        <div class="onboarding-box">
            <b>Crie minutas perfeitas em segundos.</b><br>
            Selecione o tipo, informe as partes e deixe a IA redigir as cláusulas baseadas na lei.
        </div>
        """, unsafe_allow_html=True)
        
    c1, c2, c3 = st.columns([1,1,1])
    c1.markdown(f"**1. Dados** {'✅' if step > 1 else '🟦'}")
    c2.markdown(f"**2. Minuta** {'✅' if step > 2 else ('🟦' if step==2 else '⬜')}")
    c3.markdown(f"**3. Baixar** {'✅' if step > 3 else ('🟦' if step==3 else '⬜')}")
    st.progress(int(step/3 * 100))

    if step == 1:
        with st.container(border=True):
            tipo = st.selectbox("Modelo:", ["Prestação de Serviços", "Locação de Imóvel", "Compra e Venda Imóvel", "Compra e Venda Veículo", "Outro"])
            partes = st.text_area("Partes (Contratante/Contratado)")
            objeto = st.text_area("Objeto (O que está sendo negociado?)")
            if st.button("Gerar Minuta ➔", type="primary", use_container_width=True):
                if partes and objeto:
                    with st.spinner("Redigindo cláusulas..."):
                        lei = "Lei do Inquilinato" if "Locação" in tipo else "Código Civil"
                        prompt = f"Crie contrato de {tipo}. Base: {lei}. Partes: {partes}. Objeto: {objeto}. JSON: {{'clauses': [{{'titulo': '...', 'conteudo': '...'}}]}}"
                        res = call_gemini("JSON only.", prompt, json_mode=True)
                        data = extract_json_surgical(res)
                        if data and 'clauses' in data:
                            st.session_state.contract_meta = {"tipo": tipo, "partes": partes, "objeto": objeto}
                            st.session_state.contract_clauses = data['clauses']
                            st.session_state.contract_step = 2
                            add_xp(25)
                            st.rerun()
                        else: st.error("Erro ao gerar minuta.")
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
        if docx: st.download_button("💾 Baixar DOCX", docx, "Contrato.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary", use_container_width=True)
        if st.button("✏️ Editar"): st.session_state.contract_step=2; st.rerun()

# --- 3. MESTRE DOS EDITAIS ---
elif menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais")
    
    # ONBOARDING MESTRE
    if not st.session_state.edital_text:
        st.markdown("""
        <div class="onboarding-box">
            <h4>🚀 Professor de Edital</h4>
            <p>Transforme aquele PDF gigante em um simulador de prova.</p>
            <ul>
                <li><b>Carregue:</b> Faça upload do edital.</li>
                <li><b>Treine:</b> A IA gera questões técnicas baseadas no conteúdo.</li>
                <li><b>Aprenda:</b> Receba correções com explicação detalhada.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    def gerar_turbo(dificuldade, foco):
        st.session_state.quiz_data = None
        st.session_state.quiz_show_answer = False
        with st.spinner(f"⚡ Criando questão ({dificuldade})..."):
            tema = f"FOCO: {foco}." if foco else "Tema aleatório."
            txt = st.session_state.edital_text[:15000]
            res = call_gemini("JSON Only.", f"Role: Banca. Task: Questão técnica. IGNORE: Datas/Regras. {tema} Nível: {dificuldade}. JSON Output: {{'materia':'...','enunciado':'...','alternativas':{{'A':'...','B':'...','C':'...','D':'...'}},'correta':'A','explicacao':'...'}}\nEDITAL:\n{txt}", json_mode=True)
            data = extract_json_surgical(res)
            if data: st.session_state.quiz_data = data
            else: st.error("Erro rápido.")

    if not st.session_state.edital_text:
        f = st.file_uploader("Upload PDF", type=["pdf"])
        if f and f.name != st.session_state.edital_filename:
            with st.spinner("Lendo..."):
                txt = read_pdf_safe(f)
                if txt: st.session_state.edital_text=txt; st.session_state.edital_filename=f.name; st.rerun()
                else: st.error("PDF sem texto (imagem).")
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
            if st.button("🔥 GERAR", type="primary", use_container_width=True): gerar_turbo(diff, foco); st.rerun()

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
                if st.button("➡️ Próxima", type="primary"): gerar_turbo(diff, foco); st.rerun()

# --- 4. CARTÓRIO OCR (EXPLICATIVO) ---
elif menu == "🏢 Cartório OCR":
    st.title("🏢 Cartório OCR (Digitalizador)")
    
    st.markdown("""
    <div class="onboarding-box">
        <h4>📸 Do Papel para o Digital</h4>
        <p>Ferramenta essencial para digitalizar livros de registro antigos e manuscritos.</p>
        <ul>
            <li><b>O que é OCR?</b> Reconhecimento Óptico de Caracteres. A IA "lê" a imagem.</li>
            <li><b>Como usar:</b> Tire uma foto da página do livro (Registro de Nascimento, Casamento, etc) e envie aqui.</li>
            <li><b>Resultado:</b> Receba o texto digitado pronto para copiar na <b>Certidão de Inteiro Teor</b>.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    img_file = st.file_uploader("Envie a foto do Livro/Documento", type=["png", "jpg", "jpeg"])
    if img_file:
        try:
            image = Image.open(img_file)
            st.image(image, caption="Imagem Carregada", use_container_width=True)
            if st.button("🔍 Extrair Texto (Inteiro Teor)", type="primary"):
                with st.spinner("A IA está lendo o documento..."):
                    res = call_gemini("Você é um especialista em OCR de cartório. Transcreva TODO o texto desta imagem com precisão total, mantendo nomes, datas e grafias originais.", "Transcreva esta imagem.", image=image)
                    st.text_area("Texto Extraído:", res, height=400)
                    add_xp(30)
        except Exception as e: st.error(f"Erro na imagem: {e}")

# --- 5. TRANSCRIÇÃO (EXPLICATIVO) ---
elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição de Áudio")
    
    st.markdown("""
    <div class="onboarding-box">
        <h4>🗣️ Voz para Texto</h4>
        <p>Ideal para audiências, reuniões, ditações ou notas de voz.</p>
        <ul>
            <li><b>Envie:</b> Arquivos de áudio (mp3, wav, m4a).</li>
            <li><b>Receba:</b> A transcrição completa e pontuada do que foi falado.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    audio_file = st.file_uploader("Envie o arquivo de Áudio", type=["mp3", "wav", "m4a", "ogg"])
    if audio_file:
        st.audio(audio_file)
        if st.button("📝 Transcrever Agora", type="primary"):
            with st.spinner("Ouvindo e transcrevendo... (Isso pode levar alguns segundos)"):
                # Simulação de processamento de áudio (o Gemini API Python direto aceita arquivos via File API, 
                # mas aqui simplificamos a interface. Em prod, usaríamos genai.upload_file)
                st.info("ℹ️ Para transcrição de arquivos de áudio reais, a IA precisa processar o arquivo na nuvem. (Funcionalidade demonstrativa nesta versão Local).")
                st.write("Em um app real, o texto apareceria aqui.")
