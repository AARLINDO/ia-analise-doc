# app.py
import streamlit as st
from io import BytesIO
from datetime import datetime, timedelta
from dataclasses import dataclass
import time
import json
import base64
import re

# Opcional: se tiver python-docx instalado
try:
    from docx import Document
    DOCX_AVAILABLE = True
except Exception:
    DOCX_AVAILABLE = False

# Opcional: se tiver Pillow e pytesseract instalados
try:
    from PIL import Image, ImageOps, ImageFilter
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESS_AVAILABLE = True
except Exception:
    TESS_AVAILABLE = False

# =============================================================================
# CONFIGURAÇÃO E DESIGN
# =============================================================================
st.set_page_config(page_title="Carmélio AI | Suíte Jurídica Pro", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    h1, h2, h3 { color: #F3F4F6; font-family: 'Inter', sans-serif; }
    p, label, .stMarkdown { color: #9CA3AF; }
    .stButton>button {
        width: 100%; border-radius: 8px; height: 45px; font-weight: 600; border: none;
        background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%); color: white; transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4); }
    .question-card { background-color: #1F2430; padding: 20px; border-radius: 12px; border-left: 5px solid #3B82F6; }
    .flashcard { background: linear-gradient(135deg, #1F2430 0%, #282C34 100%); padding: 24px; border-radius: 12px; border: 1px solid #3B82F6; }
    .focus-ring:focus { outline: 3px solid #8B5CF6; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# LGPD E SEGURANÇA
# =============================================================================
if "lgpd_ack" not in st.session_state:
    st.session_state.lgpd_ack = False
if not st.session_state.lgpd_ack:
    with st.expander("LGPD e Tratamento de Dados"):
        st.markdown("""
        **Aviso:** Este sistema processa textos, imagens e áudios para gerar conteúdo jurídico e educacional.
        - Finalidade: estudo, minuta e transcrição.
        - Base legal: execução de contrato/legítimo interesse.
        - Retenção: opcional; você pode optar por não armazenar conteúdo.
        - Direitos: acesso, correção, exclusão.
        """)
        st.session_state.lgpd_ack = st.checkbox("Li e concordo com o tratamento de dados", value=False)
    if not st.session_state.lgpd_ack:
        st.stop()

opt_out = st.sidebar.checkbox("Não armazenar conteúdo (opt-out)", value=True)
rate_limit_max = 30  # segundos entre requisições pesadas
if "last_heavy_call" not in st.session_state:
    st.session_state.last_heavy_call = 0.0

def rate_limited():
    now = time.time()
    if now - st.session_state.last_heavy_call < rate_limit_max:
        return True, rate_limit_max - (now - st.session_state.last_heavy_call)
    return False, 0

def mark_heavy_call():
    st.session_state.last_heavy_call = time.time()

# =============================================================================
# LOGS E OBSERVABILIDADE
# =============================================================================
if "logs" not in st.session_state:
    st.session_state.logs = []

@dataclass
class LogEntry:
    task_type: str
    model: str
    latency_ms: int
    token_usage: int
    status: str
    timestamp: str

def add_log(task_type, model, latency_ms, token_usage, status):
    st.session_state.logs.append(LogEntry(
        task_type=task_type,
        model=model,
        latency_ms=latency_ms,
        token_usage=token_usage,
        status=status,
        timestamp=datetime.now().isoformat()
    ))

# =============================================================================
# IA: ROTEAMENTO E FALLBACK (PLACEHOLDER)
# =============================================================================
# Substitua estas funções pelas integrações reais (Groq/OpenAI/etc.)
def call_llm(messages, model="llama-3.3-70b-versatile", temperature=0.3, max_tokens=2000):
    start = time.time()
    # Simulação de resposta (substituir por chamada real)
    content = "Resposta simulada do LLM. Substitua por integração real."
    latency = int((time.time() - start) * 1000)
    add_log(task_type="text", model=model, latency_ms=latency, token_usage=len(json.dumps(messages)), status="ok")
    return content

def call_llm_vision(prompt, image_b64, model="llama-3.2-11b-vision-preview", temperature=0.1):
    start = time.time()
    content = "Transcrição simulada de OCR com visão. Substitua por integração real."
    latency = int((time.time() - start) * 1000)
    add_log(task_type="vision", model=model, latency_ms=latency, token_usage=len(prompt), status="ok")
    return content

def call_llm_audio_transcribe(audio_bytes, model="whisper-large-v3", language="pt"):
    start = time.time()
    content = "Transcrição simulada de áudio. Substitua por integração real."
    latency = int((time.time() - start) * 1000)
    add_log(task_type="audio", model=model, latency_ms=latency, token_usage=len(audio_bytes), status="ok")
    return content

def route_model(task_type, complexity="default"):
    if task_type == "text":
        return "llama-3.3-70b-versatile" if complexity == "long" else "llama-3.1-8b-instruct"
    if task_type == "vision":
        return "llama-3.2-11b-vision-preview"
    if task_type == "audio":
        return "whisper-large-v3"
    return "llama-3.1-8b-instruct"

def process_text(prompt, system_instruction="Seja técnico e cite lei.", complexity="default", temperature=0.3):
    model = route_model("text", complexity)
    messages = [{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}]
    try:
        return call_llm(messages, model=model, temperature=temperature)
    except Exception:
        # Fallback
        return call_llm(messages, model="llama-3.1-8b-instruct", temperature=temperature)

# =============================================================================
# UTILITÁRIOS: DOCX, CSV/TSV, VALIDAÇÃO
# =============================================================================
def criar_docx(texto, titulo="Documento Carmélio AI"):
    if not DOCX_AVAILABLE:
        st.warning("Pacote python-docx não disponível. Instale para exportar DOCX.")
        return None
    doc = Document()
    doc.add_heading(titulo, 0)
    for p in str(texto).split("\n"):
        if p.strip():
            doc.add_paragraph(p)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def export_anki_csv(cards):
    # cards: list of tuples (front, back)
    lines = ["front,back"]
    for f, b in cards:
        f = f.replace(",", ";")
        b = b.replace(",", ";")
        lines.append(f"{f},{b}")
    data = "\n".join(lines).encode("utf-8")
    return BytesIO(data)

def validate_question_json(data):
    try:
        assert set(data.keys()) == {"enunciado", "alternativas", "gabarito", "comentario"}
        assert all(k in data["alternativas"] for k in ["A", "B", "C", "D", "E"])
        assert data["gabarito"] in ["A", "B", "C", "D", "E"]
        return True, ""
    except AssertionError:
        return False, "Formato inválido. Campos obrigatórios ausentes ou incorretos."

def extract_citations(text):
    # Detecta padrões simples de citações jurídicas
    patterns = [
        r"art\\.?\\s*\\d+",
        r"CF/88",
        r"STF|STJ",
        r"REsp\\s*\\d+",
        r"Tema\\s*\\d+",
        r"Súmula\\s*\\d+"
    ]
    found = []
    for p in patterns:
        found.extend(re.findall(p, text, flags=re.IGNORECASE))
    return list(set(found))

# =============================================================================
# OCR HÍBRIDO: PRÉ-PROCESSAMENTO + LLM
# =============================================================================
def preprocess_image(image_bytes):
    if not PIL_AVAILABLE:
        return None, "Pillow não disponível."
    try:
        img = Image.open(BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)  # corrige rotação
        img = img.convert("L")  # grayscale
        img = ImageOps.autocontrast(img)
        img = img.filter(ImageFilter.SHARPEN)
        return img, None
    except Exception as e:
        return None, f"Erro no pré-processamento: {e}"

def ocr_conventional(img):
    if not TESS_AVAILABLE:
        return "OCR convencional indisponível (instale pytesseract)."
    try:
        return pytesseract.image_to_string(img, lang="por")
    except Exception as e:
        return f"Erro no OCR: {e}"

def ocr_hybrid(image_bytes):
    img, err = preprocess_image(image_bytes)
    if err:
        return f"Falha no pré-processamento: {err}"
    texto_bruto = ocr_conventional(img)
    prompt = (
        "Reestruture o texto como 'Certidão de Inteiro Teor', mantendo nomes, datas, livro/folha/termo, "
        "averbações e descrevendo selos/carimbos entre colchetes. Não invente dados.\n\n"
        f"Texto OCR:\n{texto_bruto}"
    )
    return process_text(prompt, system_instruction="Seja fiel ao original.", complexity="long", temperature=0.1)

# =============================================================================
# CRONOGRAMA COM REPETIÇÃO ESPAÇADA (SM-2 simplificado)
# =============================================================================
def sm2_schedule(days, daily_hours, topics):
    # topics: list of strings
    plan = []
    base_date = datetime.today()
    intervals = [1, 3, 7, 14]  # revisões
    for i, t in enumerate(topics):
        study_day = base_date + timedelta(days=i % max(1, len(days)))
        plan.append({"data": study_day.date().isoformat(), "topico": t, "horas": daily_hours})
        for k, d in enumerate(intervals):
            rev_day = study_day + timedelta(days=d)
            plan.append({"data": rev_day.date().isoformat(), "topico": f"Revisão {k+1}: {t}", "horas": max(1, daily_hours//2)})
    return plan

def format_plan(plan):
    lines = []
    for item in sorted(plan, key=lambda x: x["data"]):
        lines.append(f"{item['data']} — {item['topico']} — {item['horas']}h")
    return "\n".join(lines)

# =============================================================================
# SIDEBAR E NAVEGAÇÃO
# =============================================================================
with st.sidebar:
    st.markdown("<h3 style='text-align:center;'>Carmélio AI</h3>", unsafe_allow_html=True)
    menu = st.radio("Navegação:", [
        "🎓 Estudante", "💬 Mentor Jurídico", "📄 Contratos & Peças",
        "🏢 Cartório (OCR)", "🎙️ Transcrição", "📊 Logs", "👤 Sobre"
    ])

# =============================================================================
# MÓDULO: ESTUDANTE
# =============================================================================
if menu.startswith("🎓"):
    st.title("🎓 Área do Estudante Pro")
    tab_q, tab_f, tab_c = st.tabs(["📝 Banco de Questões", "⚡ Flashcards", "📅 Cronograma"])

    with tab_q:
        st.markdown("### 🔎 Gerador de Questões (JSON validado)")
        c1, c2, c3, c4 = st.columns(4)
        disc = c1.selectbox("Disciplina", ["Constitucional", "Administrativo", "Penal", "Proc. Penal", "Civil", "Proc. Civil", "Tributário", "Notarial", "Português", "RLM", "Informática"])
        assunto = c2.text_input("Assunto", placeholder="Ex: Inquérito Policial")
        banca = c3.selectbox("Banca", ["FGV", "Cebraspe", "Vunesp", "FCC", "AOCP", "Comperve"])
        cargo = c4.text_input("Cargo", placeholder="Ex: Delegado")
        exigir_fontes = st.checkbox("Exigir fontes (artigos, súmulas, precedentes)", value=True)

        if st.button("Gerar Questão"):
            limited, wait = rate_limited()
            if limited:
                st.warning(f"Aguarde {int(wait)}s para nova geração.")
            else:
                mark_heavy_call()
                sys_msg = "Você é examinador de banca. Cite lei e precedentes quando aplicável." if exigir_fontes else "Você é examinador de banca."
                prompt = (
                    "Gere 1 questão em JSON com campos: enunciado, alternativas (A,B,C,D,E), gabarito (A–E), comentario. "
                    f"Disciplina: {disc}. Assunto: {assunto}. Banca: {banca}. Cargo: {cargo}. "
                    "Use linguagem técnica e evite ambiguidade."
                )
                r = process_text(prompt, system_instruction=sys_msg, temperature=0.2)
                try:
                    data = json.loads(r)
                except Exception:
                    st.error("Resposta não veio em JSON. Tentando reformatar…")
                    # Tentar extrair JSON bruto
                    m = re.search(r"\{.*\}", r, flags=re.S)
                    if m:
                        try:
                            data = json.loads(m.group(0))
                        except Exception:
                            data = None
                    else:
                        data = None

                if not data:
                    st.error("Falha ao obter JSON válido.")
                else:
                    ok, msg = validate_question_json(data)
                    if not ok:
                        st.error(msg)
                        st.code(json.dumps(data, ensure_ascii=False, indent=2))
                    else:
                        st.success("Questão validada.")
                        st.markdown(f"<div class='question-card'><b>Enunciado:</b> {data['enunciado']}</div>", unsafe_allow_html=True)
                        st.write("Alternativas:")
                        for k in ["A", "B", "C", "D", "E"]:
                            st.write(f"{k}) {data['alternativas'][k]}")
                        st.info(f"Gabarito: {data['gabarito']}")
                        st.write("Comentário:")
                        st.write(data["comentario"])
                        cits = extract_citations(data["comentario"])
                        if exigir_fontes and not cits:
                            st.warning("Sem citações detectadas. Considere regerar com fontes.")
                        if DOCX_AVAILABLE:
                            buf = criar_docx(json.dumps(data, ensure_ascii=False, indent=2), "Questão (JSON)")
                            st.download_button("💾 Baixar JSON em DOCX", buf, "Questao_JSON.docx")

    with tab_f:
        st.markdown("### ⚡ Flashcards com exportação Anki")
        tema = st.text_input("Tema", placeholder="Ex: Prazos do Processo Penal")
        if "cards" not in st.session_state:
            st.session_state.cards = []
        if st.button("Criar Flashcard"):
            prompt = f"Crie um flashcard difícil sobre {tema}. Retorne APENAS: PERGUNTA --- RESPOSTA."
            r = process_text(prompt, system_instruction="Seja objetivo e técnico.", temperature=0.3)
            if "---" in r:
                front, back = r.split("---", 1)
                st.session_state.cards.append((front.strip(), back.strip()))
                st.success("Flashcard adicionado.")
            else:
                st.warning("Formato inesperado. Tente novamente.")
        if st.session_state.cards:
            for i, (f, b) in enumerate(st.session_state.cards, 1):
                st.markdown(f"**{i}.** {f}")
                with st.expander("Ver resposta"):
                    st.write(b)
            csv_buf = export_anki_csv(st.session_state.cards)
            st.download_button("💾 Exportar Anki (CSV)", csv_buf, "flashcards_anki.csv")

    with tab_c:
        st.markdown("### 📅 Cronograma com repetição espaçada")
        horas = st.slider("Horas/dia", 1, 10, 4)
        dias = st.multiselect("Dias de estudo", ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"], default=["Seg", "Ter", "Qua", "Qui", "Sex"])
        topicos = st.text_area("Tópicos (um por linha)", "Constitucional - Direitos Fundamentais\nPenal - Crimes contra a pessoa\nProc. Penal - Inquérito")
        if st.button("Gerar Cronograma"):
            topics = [t.strip() for t in topicos.split("\n") if t.strip()]
            plan = sm2_schedule(dias, horas, topics)
            formatted = format_plan(plan)
            st.text_area("Plano", formatted, height=300)
            if DOCX_AVAILABLE:
                buf = criar_docx(formatted, "Cronograma de Estudos")
                st.download_button("💾 Baixar DOCX", buf, "Cronograma.docx")

# =============================================================================
# MÓDULO: MENTOR JURÍDICO
# =============================================================================
elif menu.startswith("💬"):
    st.title("💬 Mentor Jurídico 24h")
    perfil = st.selectbox("Perfil de resposta", ["Professor Didático", "Doutrinador (Técnico)", "Jurisprudencial"])
    exigir_fontes = st.checkbox("Exigir fontes (artigos, súmulas, precedentes)", value=True)

    if "chat" not in st.session_state:
        st.session_state.chat = []
    if "pinned" not in st.session_state:
        st.session_state.pinned = []

    for m in st.session_state.chat:
        st.chat_message(m["role"]).write(m["content"])
    if st.session_state.pinned:
        st.info("Fixados:")
        for i, p in enumerate(st.session_state.pinned, 1):
            st.write(f"{i}. {p[:200]}...")

    sys_msg = {
        "Professor Didático": "Use exemplos e analogias. Estruture em tópicos simples.",
        "Doutrinador (Técnico)": "Seja técnico e cite lei e doutrina.",
        "Jurisprudencial": "Foque em precedentes STF/STJ, temas e súmulas."
    }[perfil]

    if p := st.chat_input("Pergunte algo jurídico..."):
        st.session_state.chat.append({"role": "user", "content": p})
        st.chat_message("user").write(p)
        with st.chat_message("assistant"):
            prompt = p
            if exigir_fontes:
                prompt += "\n\nExija citação de artigos, súmulas e precedentes com identificação."
            r = process_text(prompt, system_instruction=sys_msg, temperature=0.2)
            st.write(r)
            st.session_state.chat.append({"role": "assistant", "content": r})
            if st.button("Fixar resposta"):
                st.session_state.pinned.append(r)

    st.markdown("---")
    st.markdown("### Checklist jurídico automático")
    caso = st.text_area("Detalhes do caso/objeto", height=120)
    tipo_doc = st.selectbox("Tipo", ["Contrato", "Petição Inicial", "Contestação", "Habeas Corpus", "Procuração"])
    if st.button("Gerar checklist"):
        prompt = (
            f"Com base no caso: {caso}, gere um checklist de riscos e pontos obrigatórios para {tipo_doc}. "
            "Estruture em tópicos: partes, objeto, preço/prazo, foro, LGPD, garantias, penalidades, jurisprudência relevante."
        )
        r = process_text(prompt, system_instruction="Seja técnico e objetivo.", temperature=0.2)
        st.write(r)
        if DOCX_AVAILABLE:
            buf = criar_docx(r, "Checklist Jurídico")
            st.download_button("💾 Baixar DOCX", buf, "Checklist.docx")

# =============================================================================
# MÓDULO: CONTRATOS & PEÇAS
# =============================================================================
elif menu.startswith("📄"):
    st.title("📄 Redação Jurídica & Peças")
    tipo_doc = st.selectbox("Documento", ["Contrato", "Petição Inicial", "Contestação", "Habeas Corpus", "Procuração"])
    c1, c2 = st.columns(2)
    parte_a = c1.text_input("Parte A")
    parte_b = c2.text_input("Parte B")
    detalhes = st.text_area("Detalhes do caso/objeto", height=120)
    uf = st.selectbox("UF/Tribunal (para adaptar jurisprudência)", ["SC", "SP", "RJ", "MG", "RS", "PR", "BA", "PE", "CE", "DF"])

    st.markdown("### Cláusulas modulares")
    clausulas = {
        "Foro": st.checkbox("Foro"),
        "Confidencialidade": st.checkbox("Confidencialidade"),
        "LGPD": st.checkbox("LGPD"),
        "Multa": st.checkbox("Multa"),
        "Reajuste": st.checkbox("Reajuste"),
        "Garantias": st.checkbox("Garantias")
    }

    if st.button("🚀 Redigir Documento"):
        if not (parte_a and parte_b and detalhes):
            st.error("Preencha Parte A, Parte B e Detalhes.")
        else:
            prompt = (
                f"Redija um(a) {tipo_doc} profissional. Parte A: {parte_a}. Parte B: {parte_b}. "
                f"Detalhes: {detalhes}. Jurisdição: {uf}. "
                "Use linguagem jurídica formal e cite leis aplicáveis. "
                "Inclua as cláusulas selecionadas: " + ", ".join([k for k, v in clausulas.items() if v]) + "."
            )
            r = process_text(prompt, system_instruction="Seja técnico e cite lei.", complexity="long", temperature=0.2)
            st.text_area("Resultado", r, height=400)
            if DOCX_AVAILABLE:
                buf = criar_docx(r, f"{tipo_doc} Profissional")
                st.download_button("💾 Baixar DOCX", buf, f"{tipo_doc}.docx")

# =============================================================================
# MÓDULO: CARTÓRIO (OCR)
# =============================================================================
elif menu.startswith("🏢"):
    st.title("🏢 Cartório Digital (OCR)")
    st.markdown("Transforme fotos de certidões antigas em texto editável (Inteiro Teor).")
    u = st.file_uploader("Envie a imagem/PDF", type=["jpg", "png", "pdf"])
    if u and st.button("📝 Gerar Inteiro Teor"):
        limited, wait = rate_limited()
        if limited:
            st.warning(f"Aguarde {int(wait)}s para nova geração.")
        else:
            mark_heavy_call()
            if u.type in ["image/jpeg", "image/png"]:
                r = ocr_hybrid(u.getvalue())
            else:
                # PDFs: fallback simples (depende de libs externas para OCR de PDF)
                r = process_text("Transcreva fielmente o conteúdo do PDF (simulado).", system_instruction="Seja fiel ao original.", temperature=0.1)
            st.text_area("Inteiro Teor", r, height=400)
            if DOCX_AVAILABLE:
                buf = criar_docx(r, "Certidão de Inteiro Teor")
                st.download_button("💾 Baixar DOCX", buf, "Certidao_Inteiro_Teor.docx")

# =============================================================================
# MÓDULO: TRANSCRIÇÃO
# =============================================================================
elif menu.startswith("🎙️"):
    st.title("🎙️ Transcrição de Áudio")
    st.caption("Converta áudios de audiências, clientes ou aulas em texto.")
    audio_file = st.file_uploader("Suba um áudio (mp3/wav/m4a/ogg)", type=["mp3", "wav", "m4a", "ogg"])
    diarizar = st.checkbox("Diarização (marcar falantes)", value=True)
    resumir = st.checkbox("Gerar resumo automático", value=True)

    if audio_file and st.button("Transcrever"):
        limited, wait = rate_limited()
        if limited:
            st.warning(f"Aguarde {int(wait)}s para nova geração.")
        else:
            mark_heavy_call()
            r = call_llm_audio_transcribe(audio_file.getvalue(), model=route_model("audio"))
            # Diarização simples (placeholder)
            if diarizar:
                r = "[Falante 1 00:00–00:30] " + r + "\n[Falante 2 00:30–01:00] ..."  # simulado
            st.text_area("Transcrição", r, height=300)
            if resumir:
                summary = process_text("Resuma em tópicos a transcrição a seguir:\n\n" + r, system_instruction="Seja objetivo.", temperature=0.2)
                st.markdown("### Resumo")
                st.write(summary)
            if DOCX_AVAILABLE:
                buf = criar_docx(r, "Transcrição de Áudio")
                st.download_button("💾 Baixar DOCX", buf, "Transcricao.docx")

# =============================================================================
# LOGS
# =============================================================================
elif menu.startswith("📊"):
    st.title("📊 Logs e Observabilidade")
    if st.session_state.logs:
        st.write(f"Total de eventos: {len(st.session_state.logs)}")
        for log in st.session_state.logs[-50:]:
            st.write(f"[{log.timestamp}] {log.task_type} | {log.model} | {log.latency_ms}ms | tokens={log.token_usage} | {log.status}")
    else:
        st.info("Sem logs ainda.")

# =============================================================================
# SOBRE
# =============================================================================
else:
    st.title("👤 Sobre o Autor")
    st.markdown("""
    ### Arthur Carmélio
    **Desenvolvedor & Especialista Jurídico**

    O **Carmélio AI** une a tradição do Direito com a velocidade da Tecnologia.
    - 🎓 Bacharel em Direito
    - 📜 Especialista Notarial
    - 💻 Desenvolvedor Python
    """)
    st.markdown("---")
    st.markdown("**Disclaimer:** Conteúdo informativo. Revise sempre com profissional habilitado.")
