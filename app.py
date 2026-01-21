# app.py
import streamlit as st
from io import BytesIO
import json
import re
import base64
import time
from datetime import datetime
# Opcional: python-docx
try:
    from docx import Document
    DOCX_AVAILABLE = True
except Exception:
    DOCX_AVAILABLE = False

# Opcional: pdfplumber e python-docx para leitura de arquivos
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except Exception:
    PDFPLUMBER_AVAILABLE = False

try:
    import docx as docx_reader
    DOCX_READER_AVAILABLE = True
except Exception:
    DOCX_READER_AVAILABLE = False

# =============================================================================
# CONFIGURAÇÃO E DESIGN
# =============================================================================
st.set_page_config(page_title="Carmélio AI | Estudante & Editais", page_icon="⚖️", layout="wide")
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
    .question-card { background-color: #1F2430; padding: 16px; border-radius: 12px; border-left: 5px solid #3B82F6; margin-bottom: 12px; }
    .focus-ring:focus { outline: 3px solid #8B5CF6; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# ESTADO
# =============================================================================
if "edital_text" not in st.session_state:
    st.session_state.edital_text = ""
if "edital_topics" not in st.session_state:
    st.session_state.edital_topics = []
if "generated_questions" not in st.session_state:
    st.session_state.generated_questions = []
if "last_heavy_call" not in st.session_state:
    st.session_state.last_heavy_call = 0.0

RATE_LIMIT_SECONDS = 20

def rate_limited():
    now = time.time()
    if now - st.session_state.last_heavy_call < RATE_LIMIT_SECONDS:
        return True, RATE_LIMIT_SECONDS - (now - st.session_state.last_heavy_call)
    return False, 0

def mark_heavy_call():
    st.session_state.last_heavy_call = time.time()

# =============================================================================
# IA PLACEHOLDER (SUBSTITUA PELAS SUAS INTEGRAÇÕES)
# =============================================================================
def call_llm(messages, model="llama-3.3-70b-versatile", temperature=0.2):
    # Simulação de resposta—substitua por Groq/OpenAI
    return "Resposta simulada do LLM. Substitua por integração real."

def process_text(prompt, system_instruction="Seja técnico e cite lei.", temperature=0.2):
    messages = [{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}]
    try:
        return call_llm(messages, temperature=temperature)
    except Exception:
        return "Falha na chamada de IA (simulada)."

# =============================================================================
# UTILITÁRIOS
# =============================================================================
def criar_docx(texto, titulo="Documento Carmélio AI"):
    if not DOCX_AVAILABLE:
        st.warning("python-docx não instalado. Instale para exportar DOCX.")
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

def validate_question_json(data):
    try:
        assert set(data.keys()) == {"enunciado", "alternativas", "gabarito", "comentario"}
        assert all(k in data["alternativas"] for k in ["A", "B", "C", "D", "E"])
        assert data["gabarito"] in ["A", "B", "C", "D", "E"]
        return True, ""
    except AssertionError:
        return False, "Formato inválido. Campos obrigatórios ausentes ou incorretos."

def extract_json_from_text(text):
    # Tenta extrair JSON de uma resposta livre
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

def extract_text_from_pdf(file_bytes):
    if not PDFPLUMBER_AVAILABLE:
        return None, "pdfplumber não instalado."
    try:
        text = ""
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text, None
    except Exception as e:
        return None, f"Erro ao ler PDF: {e}"

def extract_text_from_docx(file_bytes):
    if not DOCX_READER_AVAILABLE:
        return None, "python-docx (reader) não instalado."
    try:
        f = BytesIO(file_bytes)
        doc = docx_reader.Document(f)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text, None
    except Exception as e:
        return None, f"Erro ao ler DOCX: {e}"

def verticalize_edital(text):
    # Prompt para verticalização (tabela/estrutura)
    prompt = (
        "Extraia e liste os tópicos do edital abaixo, organizando por matéria e subtemas. "
        "Retorne em JSON com campos: 'materia', 'topicos' (lista de strings). "
        "Edital:\n" + text
    )
    r = process_text(prompt, system_instruction="Estruture em JSON válido.", temperature=0.1)
    data = extract_json_from_text(r)
    if not data:
        # Fallback simples: dividir por linhas e heurística
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        materias = {}
        current = "Geral"
        for ln in lines:
            if ln.isupper() and len(ln) > 3:
                current = ln
                materias[current] = []
            else:
                materias.setdefault(current, []).append(ln)
        # Converte para lista de objetos
        return [{"materia": m, "topicos": t} for m, t in materias.items()]
    # Se veio JSON, padroniza
    if isinstance(data, dict):
        # pode ser {"materias":[...]}
        if "materias" in data and isinstance(data["materias"], list):
            return data["materias"]
    if isinstance(data, list):
        return data
    return [{"materia": "Geral", "topicos": [text[:200] + "..."]}]

# =============================================================================
# LISTAS EXPANDIDAS
# =============================================================================
DISCIPLINAS = [
    "Direito Constitucional", "Direito Administrativo", "Direito Penal", "Direito Civil",
    "Processo Penal", "Processo Civil", "Direito Tributário", "Direito do Trabalho",
    "Processo do Trabalho", "Direito Empresarial", "Direitos Humanos", "Direito Ambiental",
    "Direito Internacional", "Notarial e Registral", "Português", "RLM", "Informática", "Ética Profissional"
]
BANCAS = ["FGV", "Cebraspe", "Vunesp", "FCC", "AOCP", "Comperve", "IBFC", "Quadrix"]
UFS = ["SC", "SP", "RJ", "MG", "RS", "PR", "BA", "PE", "CE", "DF", "GO", "ES", "MT", "MS", "PA", "AM", "RN", "PB", "PI", "RO", "RR", "TO", "AC", "AL", "AP", "SE"]

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("<h3 style='text-align:center;'>Carmélio AI</h3>", unsafe_allow_html=True)
    menu = st.radio("Navegação:", ["📑 Mestre dos Editais", "📝 Questões Inéditas", "👤 Sobre"])

# =============================================================================
# MÓDULO: MESTRE DOS EDITAIS (UPLOAD + VERTICALIZAÇÃO + TREINAMENTO)
# =============================================================================
if menu.startswith("📑"):
    st.title("📑 Mestre dos Editais")
    st.caption("Faça upload do edital (PDF/DOCX/TXT), extraia tópicos e treine a IA para gerar questões inéditas por tópico.")

    col_up, col_txt = st.columns(2)
    with col_up:
        file = st.file_uploader("Upload do edital (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
    with col_txt:
        st.write("Ou cole o texto do edital:")
        edital_text_input = st.text_area("Texto do edital", height=200)

    if st.button("📥 Processar Edital"):
        limited, wait = rate_limited()
        if limited:
            st.warning(f"Aguarde {int(wait)}s para nova operação pesada.")
        else:
            mark_heavy_call()
            text = ""
            err = None
            if file:
                if file.type == "application/pdf":
                    text, err = extract_text_from_pdf(file.getvalue())
                elif file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"]:
                    text, err = extract_text_from_docx(file.getvalue())
                elif file.type == "text/plain":
                    try:
                        text = file.getvalue().decode("utf-8", errors="ignore")
                    except Exception as e:
                        err = f"Erro ao ler TXT: {e}"
                else:
                    err = "Formato não suportado."
            else:
                text = edital_text_input

            if err:
                st.error(err)
            elif not text or len(text.strip()) < 50:
                st.warning("Texto do edital muito curto. Verifique o upload ou cole o conteúdo completo.")
            else:
                st.session_state.edital_text = text
                topics = verticalize_edital(text)
                st.session_state.edital_topics = topics
                st.success(f"Tópicos extraídos: {len(topics)} matérias.")
                for item in topics[:10]:
                    st.markdown(f"- **{item['materia']}**: {min(len(item['topicos']), 5)} tópicos")
                if DOCX_AVAILABLE:
                    buf = criar_docx(json.dumps(topics, ensure_ascii=False, indent=2), "Edital Verticalizado")
                    st.download_button("💾 Baixar tópicos (DOCX)", buf, "Edital_Verticalizado.docx")

    st.markdown("---")
    st.markdown("### 🎯 Treinar IA por tópico")
    if not st.session_state.edital_topics:
        st.info("Nenhum edital processado ainda. Faça upload ou cole o texto e clique em Processar.")
    else:
        materias = [t["materia"] for t in st.session_state.edital_topics]
        materia_sel = st.selectbox("Matéria", sorted(set(materias)))
        # Tópicos da matéria selecionada
        topicos = []
        for t in st.session_state.edital_topics:
            if t["materia"] == materia_sel:
                topicos.extend(t["topicos"])
        topico_sel = st.selectbox("Tópico", topicos)
        banca = st.selectbox("Banca simulada", BANCAS)
        cargo = st.text_input("Cargo", "Analista Judiciário")
        uf = st.selectbox("UF/Tribunal", UFS)
        nivel = st.selectbox("Nível de dificuldade", ["Fácil", "Médio", "Difícil"])

        if st.button("🧠 Gerar questão inédita do tópico"):
            limited, wait = rate_limited()
            if limited:
                st.warning(f"Aguarde {int(wait)}s para nova operação pesada.")
            else:
                mark_heavy_call()
                nivel_instr = {
                    "Fácil": "Use linguagem simples, conceito básico e alternativa correta evidente.",
                    "Médio": "Exija interpretação e aplicação prática moderada, com alternativas plausíveis.",
                    "Difícil": "Inclua nuances, jurisprudência e pegadinhas típicas da banca."
                }[nivel]
                prompt = (
                    "Gere 1 questão inédita em JSON com campos: enunciado, alternativas (A,B,C,D,E), gabarito (A–E), comentario. "
                    f"Matéria: {materia_sel}. Tópico: {topico_sel}. Banca: {banca}. Cargo: {cargo}. Jurisdição: {uf}. "
                    f"Nível: {nivel}. {nivel_instr} "
                    "Cite artigos e precedentes quando aplicável. Retorne APENAS JSON."
                )
                r = process_text(prompt, system_instruction="Você é examinador de banca. Seja técnico e cite lei.", temperature=0.2)
                data = extract_json_from_text(r)
                if not data:
                    st.error("Falha ao obter JSON válido. Tente novamente.")
                else:
                    ok, msg = validate_question_json(data)
                    if not ok:
                        st.error(msg)
                        st.code(json.dumps(data, ensure_ascii=False, indent=2))
                    else:
                        st.session_state.generated_questions.append(data)
                        st.success("Questão gerada e validada.")
                        st.markdown(f"<div class='question-card'><b>Enunciado:</b> {data['enunciado']}</div>", unsafe_allow_html=True)
                        st.write("Alternativas:")
                        for k in ["A", "B", "C", "D", "E"]:
                            st.write(f"{k}) {data['alternativas'][k]}")
                        st.info(f"Gabarito: {data['gabarito']}")
                        st.write("Comentário:")
                        st.write(data["comentario"])
                        if DOCX_AVAILABLE:
                            buf = criar_docx(json.dumps(data, ensure_ascii=False, indent=2), "Questão (JSON)")
                            st.download_button("💾 Baixar JSON em DOCX", buf, "Questao_JSON.docx")

    st.markdown("---")
    st.markdown("### 📦 Histórico de questões geradas")
    if st.session_state.generated_questions:
        st.write(f"Total: {len(st.session_state.generated_questions)}")
        for i, q in enumerate(st.session_state.generated_questions[-10:], 1):
            st.write(f"**{i}.** {q['enunciado'][:120]}...")
        if DOCX_AVAILABLE:
            buf = criar_docx(json.dumps(st.session_state.generated_questions, ensure_ascii=False, indent=2), "Histórico de Questões")
            st.download_button("💾 Baixar histórico (DOCX)", buf, "Questoes_Historico.docx")
    else:
        st.info("Nenhuma questão gerada ainda.")

# =============================================================================
# MÓDULO: QUESTÕES INÉDITAS (SEM EDITAL, LIVRE)
# =============================================================================
elif menu.startswith("📝"):
    st.title("📝 Questões Inéditas (Livre)")
    st.caption("Gere questões sem depender de edital. Escolha disciplina, banca, cargo, UF e nível.")

    c1, c2, c3 = st.columns(3)
    disc = c1.selectbox("Disciplina", DISCIPLINAS)
    banca = c2.selectbox("Banca", BANCAS)
    uf = c3.selectbox("UF/Tribunal", UFS)
    assunto = st.text_input("Assunto/Tópico", "Inquérito Policial")
    cargo = st.text_input("Cargo", "Delegado")
    nivel = st.selectbox("Nível de dificuldade", ["Fácil", "Médio", "Difícil"])

    if st.button("Gerar Questão"):
        limited, wait = rate_limited()
        if limited:
            st.warning(f"Aguarde {int(wait)}s para nova operação pesada.")
        else:
            mark_heavy_call()
            nivel_instr = {
                "Fácil": "Use linguagem simples, conceito básico e alternativa correta evidente.",
                "Médio": "Exija interpretação e aplicação prática moderada, com alternativas plausíveis.",
                "Difícil": "Inclua nuances, jurisprudência e pegadinhas típicas da banca."
            }[nivel]
            prompt = (
                "Gere 1 questão inédita em JSON com campos: enunciado, alternativas (A,B,C,D,E), gabarito (A–E), comentario. "
                f"Disciplina: {disc}. Assunto: {assunto}. Banca: {banca}. Cargo: {cargo}. Jurisdição: {uf}. "
                f"Nível: {nivel}. {nivel_instr} "
                "Cite artigos e precedentes quando aplicável. Retorne APENAS JSON."
            )
            r = process_text(prompt, system_instruction="Você é examinador de banca. Seja técnico e cite lei.", temperature=0.2)
            data = extract_json_from_text(r)
            if not data:
                st.error("Falha ao obter JSON válido. Tente novamente.")
            else:
                ok, msg = validate_question_json(data)
                if not ok:
                    st.error(msg)
                    st.code(json.dumps(data, ensure_ascii=False, indent=2))
                else:
                    st.success("Questão gerada e validada.")
                    st.markdown(f"<div class='question-card'><b>Enunciado:</b> {data['enunciado']}</div>", unsafe_allow_html=True)
                    st.write("Alternativas:")
                    for k in ["A", "B", "C", "D", "E"]:
                        st.write(f"{k}) {data['alternativas'][k]}")
                    st.info(f"Gabarito: {data['gabarito']}")
                    st.write("Comentário:")
                    st.write(data["comentario"])
                    if DOCX_AVAILABLE:
                        buf = criar_docx(json.dumps(data, ensure_ascii=False, indent=2), "Questão (JSON)")
                        st.download_button("💾 Baixar JSON em DOCX", buf, "Questao_JSON.docx")

# =============================================================================
# SOBRE
# =============================================================================
else:
    st.title("👤 Sobre")
    st.markdown("""
    **Carmélio AI** — Suíte jurídica para estudantes e profissionais.
    - Upload e verticalização de editais
    - Geração de questões inéditas por tópico
    - Níveis de dificuldade e adaptação por UF/Tribunal
    """)
    st.markdown("---")
    st.markdown("**Disclaimer:** Conteúdo informativo. Revise sempre com profissional habilitado.")
