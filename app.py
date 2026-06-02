import streamlit as st
import streamlit.components.v1 as components
import os
import json
import time
import re
import random
from datetime import datetime, date
from io import BytesIO

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Ultimate Studio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 2. IMPORTAÇÕES E SETUP
# =============================================================================
try: 
    import google.generativeai as genai
except ImportError: 
    genai = None

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
    from PIL import Image, ImageDraw, ImageFont
except ImportError: 
    Image = None

# Inicialização de Estado (Session State) com as melhorias de Retenção e Radar
keys = {
    "user_xp": 0, "contract_step": 1, "contract_clauses": [], 
    "contract_meta": {}, "chat_history": [], "edital_text": "", 
    "edital_filename": "", "quiz_data": None, "quiz_show_answer": False, 
    "user_choice": None, "ocr_text": "", "last_call": 0, "audio_text": "",
    "oab_quiz_data": None, 
    "oab_show_answer": False, 
    "oab_choice": None,
    "oab_click_count": 0,
    "caderno_erros": [],
    # --- CHAVES DE RETENÇÃO ---
    "oab_stats": {"total": 0, "acertos": 0, "erros": 0, "materias": {}},
    "historico_oab": [],
    "favoritas": [],
    "coach_cronograma": None
}
for k, v in keys.items():
    if k not in st.session_state: 
        st.session_state[k] = v

# =============================================================================
# 3. FUNÇÕES UTILITÁRIAS E LÓGICA (BACKEND)
# =============================================================================

def check_rate_limit():
    if time.time() - st.session_state.last_call < 2.0: 
        return True 
    return False

def mark_call(): 
    st.session_state.last_call = time.time()

def add_xp(amount):
    st.session_state.user_xp += amount
    st.toast(f"+{amount} XP obtidos!", icon="⚡")

def get_rank_badge(xp):
    """Sistema de Ranking Interno baseado no XP acumulado pelo estudante."""
    if xp >= 1500: return "💎 Estudante Diamante"
    elif xp >= 800: return "🥇 Estudante Ouro"
    elif xp >= 300: return "🥈 Estudante Prata"
    return "🏆 Estudante Bronze"

@st.cache_resource
def get_best_model():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key: 
        return None, "⚠️ Configure secrets.toml"
    try:
        genai.configure(api_key=api_key)
        try: 
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except: 
            return None, "Erro de Chave API"
        
        pref = ['models/gemini-1.5-pro', 'models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-pro']
        escolhido = next((m for m in pref if m in models), models[0] if models else None)
        
        if escolhido: 
            return genai.GenerativeModel(escolhido.replace("models/", "")), escolhido.replace("models/", "")
        return None, "Nenhum modelo compatível."
    except Exception as e: 
        return None, f"Erro Fatal: {str(e)}"

def call_gemini(system_prompt, user_prompt, json_mode=False, image=None, audio_bytes=None, audio_mime=None, use_search=False):
    if check_rate_limit(): time.sleep(1)
    mark_call()
    model, name = get_best_model()
    if not model: return f"Erro: {name}"
    try:
        tools_config = 'google_search_retrieval' if use_search else None
        if audio_bytes:
            audio_part = {"mime_type": audio_mime, "data": audio_bytes}
            return model.generate_content([system_prompt, audio_part, user_prompt]).text
        if image:
            return model.generate_content([system_prompt, image, user_prompt]).text
            
        full_prompt = f"SYSTEM ROLE: {system_prompt}\nUSER REQUEST: {user_prompt}"
        if json_mode: full_prompt += "\nFORMAT: Return ONLY valid JSON. No Markdown."
        
        response = model.generate_content(full_prompt, tools=tools_config) if tools_config else model.generate_content(full_prompt)
        return response.text
    except Exception as e: 
        if "429" in str(e): return "⚠️ Limite de velocidade atingido. Aguarde 30 segundos."
        return f"Erro IA: {str(e)}"

def extract_json_surgical(text):
    try:
        text = text.replace("```json", "").replace("
```", "")
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
                if i >= 300: break 
                text += (p.extract_text() or "") + "\n"
        return text if text.strip() else None
    except: pass
    return None

def create_generic_docx(content, title="Documento Carmélio AI"):
    if not docx: return None
    doc = Document()
    doc.add_heading(title, 0)
    for line in content.split('\n'):
        if line.strip(): doc.add_paragraph(line.strip())
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

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
        for line in clause.get('conteudo', '').split('\n'):
            if line.strip(): doc.add_paragraph(line.strip())
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_performance_card(acertos, total, taxa):
    """Gera o card de desempenho compartilhável no Instagram (Marketing Orgânico)."""
    if not Image: return None
    img = Image.new("RGB", (600, 400), color="#11141d")
    draw = ImageDraw.Draw(img)
    draw.rectangle([15, 15, 585, 385], outline="#2563EB", width=3)
    
    draw.text((300, 60), "CARMÉLIO AI", fill="#ffffff", anchor="mm")
    draw.text((300, 100), "PROJETO 40 ACERTOS | OAB 47", fill="#F59E0B", anchor="mm")
    
    draw.text((300, 180), f"Acertos: {acertos} de {total}", fill="#34D399", anchor="mm")
    draw.text((300, 240), f"Taxa de Performance: {taxa}%", fill="#4285F4", anchor="mm")
    
    draw.text((300, 330), "Rumo à Aprovação Exame de Ordem", fill="#8B949E", anchor="mm")
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def get_daily_verse():
    versiculos = [
        {"ref": "Josué 1:9", "txt": "Seja forte e corajoso! Não se apavore nem desanime, pois o Senhor, o seu Deus, estará com você por onde você andar."},
        {"ref": "Filipenses 4:13", "txt": "Tudo posso naquele que me fortalece."},
        {"ref": "Salmos 37:5", "txt": "Entregue o seu caminho ao Senhor; confie nele, e ele agirá."}
    ]
    index = date.today().timetuple().tm_yday % len(versiculos)
    return versiculos[index]

# =============================================================================
# 4. INTERFACE GRÁFICA & CSS
# =============================================================================
def safe_image_show(image_path):
    if os.path.exists(image_path):
        try: st.image(image_path, use_container_width=True)
        except TypeError: st.image(image_path, use_column_width=True)
    else: st.markdown("## ⚖️ Carmélio AI")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #11141d; border-right: 1px solid #2B2F3B; }
    .gemini-text { background: -webkit-linear-gradient(45deg, #4285F4, #9B72CB, #D96570); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 2.2rem; }
    div.stButton > button { background: linear-gradient(90deg, #2563EB 0%, #7C3AED 100%); color: white; border: none; font-weight: 600; border-radius: 8px; }
    .footer-credits { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #2B2F3B; color: #6B7280; font-size: 11px; }
    .footer-credits strong { color: #E0E0E0; }
    .onboarding-box { background-color: #1F2430; padding: 20px; border-radius: 10px; border-left: 5px solid #4285F4; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

def render_sidebar_widgets():
    v = get_daily_verse()
    html_code = f"""
    <style>
        .widget-box {{ background: #1F2430; border: 1px solid #374151; border-radius: 12px; padding: 12px; text-align: center; color: white; font-family: sans-serif; margin-bottom: 12px; }}
        .devotional-box {{ background: linear-gradient(135deg, #1e293b, #0f172a); border-left: 4px solid #F59E0B; text-align: left; padding: 12px; margin-bottom: 15px; border-radius: 8px; }}
        .verse-text {{ font-style: italic; font-size: 12px; color: #E2E8F0; margin-bottom: 5px; }}
        .verse-ref {{ font-size: 10px; font-weight: bold; color: #F59E0B; text-align: right; }}
        .time-display {{ font-size: 34px; font-weight: 800; margin: 6px 0; color: #4285F4; }}
        .config-label {{ font-size: 10px; color: #8B949E; font-weight: bold; margin-top: 6px; margin-bottom: 3px; text-align: left; padding-left: 4px; }}
        .selector-group {{ display: flex; justify-content: space-between; background: #11141d; padding: 2px; border-radius: 6px; margin-bottom: 8px; }}
        .selector-btn {{ flex: 1; background: transparent; border: none; color: #8B949E; padding: 4px 0; font-size: 11px; font-weight: 600; cursor: pointer; border-radius: 4px; transition: all 0.2s; }}
        .selector-btn.active {{ background: #2563EB; color: white; }}
        .btn {{ border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; margin: 2px; font-size: 12px; font-weight: bold; color: white; }}
        .btn-primary {{ background: #2563EB; }}
        .btn-warn {{ background: #D97706; }}
        .btn-danger {{ background: #DC2626; }}
        audio {{ width: 100%; margin-top: 10px; }}
    </style>
    
    <div class="devotional-box">
        <div style="color:#F59E0B;font-size:11px;font-weight:bold;margin-bottom:4px;">📖 Palavra do Dia</div>
        <div class="verse-text">"{v['txt']}"</div>
        <div class="verse-ref">{v['ref']}</div>
    </div>
    
    <div class="widget-box">
        <div style="font-size:11px;font-weight:bold;color:#8B949E;margin-bottom:2px;">TOMATO FOCUS</div>
        
        <div class="config-label">TEMPO DE FOCO</div>
        <div class="selector-group">
            <button class="selector-btn" id="foco-25" onclick="setConfigFoco(25)">25m</button>
            <button class="selector-btn" id="foco-35" onclick="setConfigFoco(35)">35m</button>
            <button class="selector-btn" id="foco-45" onclick="setConfigFoco(45)">45m</button>
        </div>

        <div class="config-label">INTERVALO</div>
        <div class="selector-group">
            <button class="selector-btn" id="break-5" onclick="setConfigBreak(5)">5m</button>
            <button class="selector-btn" id="break-10" onclick="setConfigBreak(10)">10m</button>
            <button class="selector-btn" id="break-15" onclick="setConfigBreak(15)">15m</button>
        </div>

        <div class="time-display" id="timer">25:00</div>
        <div id="status" style="font-size:10px;color:#aaa;margin-bottom:8px;">Pronto</div>
        
        <div>
            <button class="btn btn-primary" onclick="startTimer()">▶</button>
            <button class="btn btn-warn" onclick="pauseTimer()">⏸</button>
            <button class="btn btn-danger" onclick="resetTimer()">↺</button>
        </div>
    </div>
    
    <div class="widget-box">
        <div style="font-size:11px;font-weight:bold;color:#8B949E;margin-bottom:10px;">🎵 Rádio LoFi 24h</div>
        <audio controls><source src="https://stream.zeno.fm/f3wvbbqmdg8uv" type="audio/mpeg"></audio>
        <div style="font-size:10px;color:#34D399;margin-top:8px;">Clique em Play para ouvir</div>
    </div>

    <script>
        let interval = null;
        let cfgFoco = localStorage.getItem('pomodoro_cfg_foco') ? parseInt(localStorage.getItem('pomodoro_cfg_foco')) : 25;
        let cfgBreak = localStorage.getItem('pomodoro_cfg_break') ? parseInt(localStorage.getItem('pomodoro_cfg_break')) : 5;
        let time = localStorage.getItem('pomodoro_time') ? parseInt(localStorage.getItem('pomodoro_time')) : (cfgFoco * 60);
        let isModeFoco = localStorage.getItem('pomodoro_mode') === 'false' ? false : true;
        let isRunning = localStorage.getItem('pomodoro_running') === 'true' ? true : false;

        function setConfigFoco(mins) {{
            if(isRunning) return;
            cfgFoco = mins;
            localStorage.setItem('pomodoro_cfg_foco', mins);
            if(isModeFoco) {{
                time = mins * 60;
                localStorage.setItem('pomodoro_time', time);
            }}
            updateUI();
        }}

        function setConfigBreak(mins) {{
            if(isRunning) return;
            cfgBreak = mins;
            localStorage.setItem('pomodoro_cfg_break', mins);
            if(!isModeFoco) {{
                time = mins * 60;
                localStorage.setItem('pomodoro_time', time);
            }}
            updateUI();
        }}

        function updateUI() {{
            let m = Math.floor(time / 60);
            let s = time % 60;
            document.getElementById('timer').innerText = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
            document.getElementById('timer').style.color = isModeFoco ? '#4285F4' : '#34D399';
            document.getElementById('status').innerText = isRunning ? (isModeFoco ? 'Focando...' : 'Descansando...') : 'Pausado';

            ['25','35','45'].forEach(v => {{ document.getElementById('foco-'+v).classList.remove('active'); }});
            document.getElementById('foco-'+cfgFoco).classList.add('active');

            ['5','10','15'].forEach(v => {{ document.getElementById('break-'+v).classList.remove('active'); }});
            document.getElementById('break-'+cfgBreak).classList.add('active');
        }}

        function startTimer() {{
            if(interval) return;
            isRunning = true;
            localStorage.setItem('pomodoro_running', 'true');
            interval = setInterval(() => {{
                if(time > 0) {{
                    time--;
                    localStorage.setItem('pomodoro_time', time);
                    updateUI();
                }} else {{
                    clearInterval(interval);
                    interval = null;
                    if(isModeFoco) {{
                        isModeFoco = false;
                        time = cfgBreak * 60;
                        localStorage.setItem('pomodoro_mode', 'false');
                        alert('Ciclo de Foco Concluído! Hora do intervalo.');
                    }} else {{
                        isModeFoco = true;
                        time = cfgFoco * 60;
                        localStorage.setItem('pomodoro_mode', 'true');
                        alert('Fim do descanso! Iniciando foco.');
                    }}
                    localStorage.setItem('pomodoro_time', time);
                    updateUI();
                    startTimer();
                }}
            }}, 1000);
        }}

        function pauseTimer() {{
            clearInterval(interval);
            interval = null;
            isRunning = false;
            localStorage.setItem('pomodoro_running', 'false');
            updateUI();
        }}

        function resetTimer() {{
            pauseTimer();
            isModeFoco = true;
            time = cfgFoco * 60;
            localStorage.setItem('pomodoro_time', time);
            localStorage.setItem('pomodoro_mode', 'true');
            localStorage.setItem('pomodoro_running', 'false');
            updateUI();
            document.getElementById('status').innerText = 'Pronto';
        }}

        updateUI();
        if (isRunning) {{ startTimer(); }}
    </script>
    """
    components.html(html_code, height=620)

# =============================================================================
# 5. EXECUÇÃO PRINCIPAL E FLUXO DE TELAS
# =============================================================================
with st.sidebar:
    safe_image_show("carmelio_logo.png.png")
    st.caption(f"⚡ Nível Atual: **{get_rank_badge(st.session_state.user_xp)}**")
    
    render_sidebar_widgets()
    st.markdown("---")
    
    # ACESSO DIRETO E LIVRE ATIVADO SEM BARREIRAS DE SENHA
    studio_authorized = True
    st.success("Acesso Livre Ativado! 🔓")
    
    model_obj, status_msg = get_best_model()
    if not model_obj: st.error(f"❌ {status_msg}")
    else: st.success(f"🟢 **Modelo Ativo: {status_msg}**")
        
    menu = st.radio("Menu", [
        "🎓 Gabaritando a OAB", "✨ Chat Inteligente", "📝 Gere seu Contrato", 
        "🎯 Mestre dos Editais", "🏢 Cartório OCR", "🎙️ Transcrição"
    ], label_visibility="collapsed")
    
    st.markdown("---")
    st.write(f"📊 **Questões Respondidas:** {st.session_state.oab_stats['total']}")
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))
    st.markdown("""<div class='footer-credits'>Desenvolvido por<br><strong>Arthur Carmélio</strong><br>© 2026 Carmélio AI</div>""", unsafe_allow_html=True)

def verificar_acesso_premium():
    return True

# =============================================================================
# 6. RENDERIZAÇÃO DAS TELAS
# =============================================================================

if menu == "🎓 Gabaritando a OAB":
    st.title("🎓 Ecossistema de Aprovação OAB 47")
    
    t1, t2, t3, t4, t5 = st.tabs([
        "🎯 1ª Fase - Simulador FGV", "📊 Meu Desempenho & Coach", 
        "✍️ 2ª Fase - Corretora", "📚 Caderno de Erros", "⭐ Favoritas"
    ])
    
    with t1:
        st.markdown('<div class="onboarding-box"><h4>🎯 Projeto 40 Acertos</h4><p>Treine com inteligência artificial direto no banco oficial da FGV. Monitore suas estatísticas na aba ao lado.</p></div>', unsafe_allow_html=True)
        
        materias_oab = [
            "Simulado Geral (Todas as Matérias)", "Ética Profissional", "Direito Constitucional", 
            "Direito Administrativo", "Direito Penal", "Processo Penal", "Direito Civil", "Processo Civil"
        ]

        def gerar_questao_oab(materia_selecionada):
            st.session_state["oab_quiz_data"] = None
            st.session_state["oab_show_answer"] = False
            st.session_state.oab_click_count += 1
            
            with st.spinner("🔍 Buscando questão real da banca FGV..."):
                filtro = "" if "Geral" in materia_selecionada else f"especificamente da matéria de {materia_selecionada}"
                prompt = f"""
                ROLE: Professor Especialista em OAB da FGV.
                TASK: Forneça uma QUESTÃO REAL E OFICIAL de exames passados da OAB aplicada pela banca FGV, {filtro}.
                JSON Output Format: {{
                    'exame': 'Exame OAB FGV',
                    'materia': '...',
                    'enunciado': '...',
                    'alternativas': {{'A':'...', 'B':'...', 'C':'...', 'D':'...'}},
                    'correta': 'A',
                    'fundamentacao': 'Texto detalhado explicando a base jurídica geral.',
                    'artigo': 'Dispositivos legais específicos aplicados (ex: Art 5, LXXIV da CF).',
                    'pegadinha': 'Qual a armadilha conceitual clássica que a FGV tentou armar nesta questão.',
                    'dica': 'Macete rápido para o aluno lembrar no dia do exame.'
                }}
                """
                res = call_gemini("JSON Only.", prompt, json_mode=True, use_search=True)
                data = extract_json_surgical(res)
                if data: st.session_state["oab_quiz_data"] = data

        col_m, col_b = st.columns([2, 1])
        with col_m:
            mat_escolhida = st.selectbox("Escolha a disciplina para treinar:", materias_oab, key="sb_oab_new")
        with col_b:
            st.write(""); st.write("")
            if st.button("🚀 TRAZER QUESTÃO", type="primary", use_container_width=True, key="btn_oab_new"):
                gerar_questao_oab(mat_escolhida)
                st.rerun()

        if st.session_state.get("oab_quiz_data") is not None:
            q = st.session_state["oab_quiz_data"]
            st.markdown(f"### 📝 {q.get('exame', 'Exame de Ordem')} | Matéria: {q.get('materia', mat_escolhida)}")
            st.info(q['enunciado'])
            opts = q['alternativas']
            
            if st.button("⭐ Salvar nas Favoritas", key="fav_btn"):
                if q not in st.session_state.favoritas:
                    st.session_state.favoritas.append(q)
                    st.toast("Questão arquivada na aba de Favoritas!", icon="⭐")

            if not st.session_state["oab_show_answer"]:
                c1, c2 = st.columns(2)
                if c1.button(f"A) {opts['A']}", use_container_width=True, key="oa_a"): st.session_state["oab_choice"] = "A"; st.session_state["oab_show_answer"] = True; st.rerun()
                if c2.button(f"B) {opts['B']}", use_container_width=True, key="oa_b"): st.session_state["oab_choice"] = "B"; st.session_state["oab_show_answer"] = True; st.rerun()
                if c1.button(f"C) {opts['C']}", use_container_width=True, key="oa_c"): st.session_state["oab_choice"] = "C"; st.session_state["oab_show_answer"] = True; st.rerun()
                if c2.button(f"D) {opts['D']}", use_container_width=True, key="oa_d"): st.session_state["oab_choice"] = "D"; st.session_state["oab_show_answer"] = True; st.rerun()
            else:
                u, c = st.session_state["oab_choice"], q['correta']
                is_correct = (u == c)
                
                if "oab_processed" not in st.session_state:
                    st.session_state.oab_stats["total"] += 1
                    if is_correct:
                        st.session_state.oab_stats["acertos"] += 1
                    else:
                        st.session_state.oab_stats["erros"] += 1
                        if q not in st.session_state.caderno_erros:
                            st.session_state.caderno_erros.append(q)
                    
                    st.session_state.historico_oab.append({
                        "materia": q.get('materia', mat_escolhida),
                        "acertou": is_correct,
                        "data": datetime.now().strftime("%d/%m/%Y - %H:%M")
                    })
                    st.session_state["oab_processed"] = True

                for l, t in opts.items():
                    icon = "✅" if l == c else ("❌" if l == u else "⬜")
                    st.write(f"{icon} **{l})** {t}")
                
                if is_correct:
                    st.success("🎯 Sensacional! Você acertou no alvo!")
                    add_xp(60)
                else:
                    st.error(f"Faltou pouco! Resposta correta: Letra {c}")

                with st.container(border=True):
                    st.markdown("#### 📚 Correção Avançada da IA")
                    st.write(q.get('fundamentacao', 'Sem fundamentação disponível.'))
                    st.markdown(f"**⚖️ Artigo Aplicável:** {q.get('artigo', 'N/A')}")
                    st.markdown(f"**🚨 Pegadinha da FGV:** *{q.get('pegadinha', 'N/A')}*")
                    st.markdown(f"**💡 Dica para a Prova:** {q.get('dica', 'N/A')}")

                st.write("")
                if st.button("➡️ Próxima Questão", type="primary", key="nx_oab"):
                    if "oab_processed" in st.session_state: del st.session_state["oab_processed"]
                    gerar_questao_oab(mat_escolhida)
                    st.rerun()

    with t2:
        st.subheader("📊 Radar de Performance OAB")
        
        st_t = st.session_state.oab_stats["total"]
        st_a = st.session_state.oab_stats["acertos"]
        st_e = st.session_state.oab_stats["erros"]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Respondidas", st_t)
        c2.metric("Acertos Totais", st_a, delta=f"+{st_a} acertos", delta_color="inverse")
        c3.metric("Erros Registrados", st_e)
        
        if st_t > 0:
            taxa_calculada = round((st_a / st_t) * 100, 1)
            st.metric("Taxa de Acertos Geral", f"{taxa_calculada}%")
            
            st.markdown("### 📈 Diagnóstico Real de Aprovação")
            if st_t < 10:
                st.info("ℹ️ Responda pelo menos 10 questões para o sistema calcular sua probabilidade de aprovação.")
            else:
                if taxa_calculada >= 75:
                    st.success(f"🔥 **Excelente chance de aprovação ({taxa_calculada}%):** Sua base de dados conceitual está sólida. Continue firme nos simulados!")
                elif taxa_calculada >= 55:
                    st.warning(f"⚠️ **Zona de Atenção ({taxa_calculada}%):** Você está muito perto, mas oscilando. Force revisões no seu caderno de erros.")
                else:
                    st.error(f"🚨 **Alerta de Risco ({taxa_calculada}%):** Risco alto de reprovação se a prova fosse hoje. Intensifique os estudos.")

            st.markdown("---")
            st.markdown("#### 📸 Compartilhe suas conquistas no Instagram!")
            card_btn = generate_performance_card(st_a, st_t, taxa_calculada)
            if card_btn:
                st.download_button("📸 Baixar Card de Desempenho", card_btn, "Desempenho_OAB.png", "image/png")
        else:
            st.info("Comece a treinar na aba ao lado para gerar seu radar estatístico.")

        st.markdown("---")
        st.subheader("🎯 Coach IA: Cronograma Tático Automatizado")
        cc1, cc2 = st.columns(2)
        dias_r = cc1.number_input("Dias até a prova da OAB:", min_value=1, max_value=365, value=45)
        horas_d = cc2.slider("Horas por dia que você pretende dedicar:", 1, 12, 3)
        
        if st.button("🗺️ GERAR MEU CRONOGRAMA INTEGRADO", type="primary"):
            with st.spinner("IA calculando pontos de recorrência da FGV..."):
                prompt_coach = f"Crie um planejamento estratégico de estudos para a OAB 1ª Fase. Dias disponíveis: {dias_r}, Horas por dia: {horas_d}. Distribua o tempo dando prioridade máxima para Ética (8 questões), Constitucional, Administrativo, Civil e Penal. Retorne em formato Markdown estruturado."
                st.session_state.coach_cronograma = call_gemini("Você é um Coach Mentor especialista em Exame de Ordem.", prompt_coach)
        
        if st.session_state.coach_cronograma:
            st.markdown(st.session_state.coach_cronograma)

        st.markdown("---")
        st.subheader("📋 Histórico de Treinos (Últimas 20)")
        if st.session_state.historico_oab:
            for item in reversed(st.session_state.historico_oab[-20:]):
                status_h = "✅ Acertou" if item["acertou"] else "❌ Errou"
                st.write(f"• **[{item['data']}]** {item['materia']} — {status_h}")
        else:
            st.caption("Histórico vazio.")

    with t3:
        st.subheader("🤖 Banca Examinadora: Peças Processuais 2ª Fase")
        area_2f = st.selectbox("Área do Exame:", ["Direito Penal", "Direito Civil", "Direito Constitucional", "Direito do Trabalho"])
        peca_txt = st.text_area("Cole sua peça simulada para escaneamento estrutural da banca:", height=300)
        if st.button("⚖️ ANALISAR PEÇA", type="primary"):
            if peca_txt:
                with st.spinner("Avaliando técnica estrutural e adequação de pedidos..."):
                    res_peca = call_gemini("Membro da banca examinadora FGV.", f"Dê nota de 0 a 5.0 e aponte erros estruturais e de fundamentação na peça de {area_2f}: \n{peca_txt}")
                    st.markdown(res_peca)
            else: st.error("Cole o texto da peça jurídica.")

    with t4:
        st.subheader("📚 Caderno de Erros Inteligente")
        if not st.session_state.caderno_erros:
            st.info("Seu caderno está limpo! Erros cometidos no simulador serão salvos aqui automaticamente.")
        else:
            for i, err in enumerate(st.session_state.caderno_erros):
                with st.expander(f"❌ Questão {i+1} - Matéria: {err.get('materia')}"):
                    st.write(err["enunciado"])
                    st.warning(f"Gabarito Oficial: Letra {err['correta']}")
                    st.write(f"**Revisão:** {err.get('fundamentacao')}")

    with t5:
        st.subheader("⭐ Minhas Questões Favoritas")
        if not st.session_state.favoritas:
            st.info("Você ainda não salvou nenhuma questão. Marque as mais complexas no simulador principal.")
        else:
            for idx, fav in enumerate(st.session_state.favoritas):
                with st.expander(f"⭐ Favorita {idx+1} | {fav.get('materia')}"):
                    st.write(fav["enunciado"])
                    st.info(f"Gabarito Correto: {fav['correta']}")
                    st.write(fav.get('fundamentacao'))

# =============================================================================
# OUTROS MÓDULOS JURÍDICOS (ACESSO DIRETO)
# =============================================================================

elif menu == "✨ Chat Inteligente":
    st.markdown('<h1 class="gemini-text">Mentor Jurídico</h1>', unsafe_allow_html=True)
    if not st.session_state.chat_history: 
        st.markdown("""<div class="onboarding-box"><h4>👋 Bem-vindo ao Modo Direto</h4><p>Sou seu <b>Mentor Jurídico</b> de acesso livre. Dúvidas, consultas, petições ou jurisprudências?</p></div>""", unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"], avatar="🧑‍⚖️" if msg["role"] == "user" else "🤖"): st.markdown(msg["content"])
    if p := st.chat_input("Digite sua dúvida legal aqui..."):
        st.session_state.chat_history.append({"role": "user", "content": p})
        with st.chat_message("user", avatar="🧑‍⚖️"): st.write(p)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analisando bases..."):
                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history[-6:]])
                res = call_gemini("Advogado Sênior experiente.", history, use_search=True)
                st.write(res)
                st.session_state.chat_history.append({"role": "assistant", "content": res})
                add_xp(5)

elif menu == "📝 Gere seu Contrato":
    st.title("📝 Gerador Inteligente de Contratos")
    step = st.session_state.contract_step
    c1, c2, c3 = st.columns([1,1,1])
    c1.markdown(f"**1. Dados** {'✅' if step > 1 else '🟦'}")
    c2.markdown(f"**2. Minuta** {'✅' if step > 2 else ('🟦' if step==2 else '⬜')}")
    c3.markdown(f"**3. Baixar** {'✅' if step > 3 else ('🟦' if step==3 else '⬜')}")
    st.progress(int(step/3 * 100))

    if step == 1:
        with st.container(border=True):
            tipo = st.selectbox("Modelo Contratual:", ["Prestação de Serviços", "Locação de Imóvel", "Compra e Venda Imóvel", "Outro"])
            partes = st.text_area("Qualificação Completa das Partes:")
            objeto = st.text_area("Descreva detalhadamente o Objeto e Valores:")
            if st.button("Gerar Minuta Estrutural ➔", type="primary", use_container_width=True):
                if partes and objeto:
                    with st.spinner("Redigindo cláusulas com IA jurídica..."):
                        prompt = f"Crie contrato de {tipo}. Partes: {partes}. Objeto: {objeto}. JSON: {{'clauses': [{{'titulo': '...', 'conteudo': '...'}}]}}"
                        res = call_gemini("JSON only.", prompt, json_mode=True)
                        data = extract_json_surgical(res)
                        if data and 'clauses' in data:
                            st.session_state.contract_meta = {"tipo": tipo, "partes": partes, "objeto": objeto}
                            st.session_state.contract_clauses = data['clauses']
                            st.session_state.contract_step = 2
                            add_xp(25)
                            st.rerun()
    elif step == 2:
        st.header("📑 Revisão de Cláusulas")
        for i, c in enumerate(st.session_state.contract_clauses):
            with st.expander(f"Cláusula: {c.get('titulo')}"):
                nt = st.text_input("Título", c['titulo'], key=f"t{i}")
                nc = st.text_area("Conteúdo", c['conteudo'], key=f"c{i}")
                st.session_state.contract_clauses[i] = {"titulo": nt, "conteudo": nc}
        if st.button("Finalizar Documento ➔", type="primary"):
            st.session_state.contract_step = 3
            st.rerun()
    elif step == 3:
        st.header("✅ Documento Pronto")
        dx = create_contract_docx(st.session_state.contract_clauses, st.session_state.contract_meta)
        if dx: st.download_button("💾 Baixar Minuta em Word (.docx)", dx, "Contrato_CarmelioAI.docx", type="primary")

elif menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais")
    if not st.session_state.edital_text:
        st.markdown('<div class="onboarding-box"><h4>🚀 Simulação Contextual de Editais</h4><p>Suba o PDF de qualquer concurso público e a inteligência artificial criará perguntas focadas puramente no conteúdo programático.</p></div>', unsafe_allow_html=True)
        f = st.file_uploader("Upload PDF do Edital", type=["pdf"])
        if f and f.name != st.session_state.edital_filename:
            with st.spinner("Escaneando anexos de conhecimentos específicos..."):
                txt = read_pdf_safe(f)
                if txt:
                    st.session_state.edital_text = txt
                    st.session_state.edital_filename = f.name
                    st.rerun()
    else:
        st.success(f"📂 Arquivo Ativo: {st.session_state.edital_filename}")
        if st.button("🗑️ Trocar Edital"):
            st.session_state.edital_text = ""
            st.rerun()

elif menu == "🏢 Cartório OCR":
    st.title("🏢 Cartório OCR (Digitalizador de Livros)")
    st.markdown('<div class="onboarding-box"><h4>📸 Transcrição Multimodal</h4><p>Otimizado para extrair textos de páginas de livros de registro antigos e certidões com alta precisão.</p></div>', unsafe_allow_html=True)
    img_file = st.file_uploader("Enviar Foto nítida do documento/página:", type=["png", "jpg", "jpeg"])
    if img_file:
        image = Image.open(img_file)
        st.image(image, use_container_width=True)
        if st.button("🔍 Extrair Texto Completo", type="primary"):
            with st.spinner("Processando OCR neural..."):
                res = call_gemini("Especialista em OCR cartorial e transcrição de livros.", "Transcreva mantendo fielmente pontuações e parágrafos.", image=image)
                st.session_state.ocr_text = res
                add_xp(30)
    if st.session_state.ocr_text: 
        st.text_area("Texto Extraído:", st.session_state.ocr_text, height=300)

elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição de Áudio Real")
    audio_file = st.file_uploader("Carregar arquivo de áudio (Audiências, depoimentos, reuniões):", type=["mp3", "wav", "m4a"])
    if audio_file:
        st.audio(audio_file)
        if st.button("📝 Iniciar Transcrição Inteligente", type="primary"):
            with st.spinner("Processando ondas sonoras..."):
                mime = "audio/mp3" if audio_file.name.endswith("mp3") else "audio/wav"
                res = call_gemini("Transcreva organizando em parágrafos e corrigindo terminologias do direito.", "Transcreva o áudio.", audio_bytes=audio_file.getvalue(), audio_mime=mime)
                st.session_state.audio_text = res
                add_xp(40)
    if st.session_state.audio_text: 
        st.text_area("Resultado:", st.session_state.audio_text, height=250)
