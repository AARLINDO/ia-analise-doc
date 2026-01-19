import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
import mimetypes
import uuid
from datetime import datetime
from docx import Document
from io import BytesIO

# ==============================================================================
# 1. CONFIGURAÇÃO INICIAL
# ==============================================================================
st.set_page_config(
    page_title="Carmélio OS",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Cores do Tema (Gemini Dark)
THEME = {
    "bg": "#131314",
    "sidebar": "#1E1F20",
    "accent": "#A8C7FA",
    "text": "#E3E3E3",
    "card": "#2D2E2F"
}

# ==============================================================================
# 2. CSS VISUAL (MICROFONE ESTILO GEMINI)
# ==============================================================================
st.markdown(f"""
<style>
    /* RESET GLOBAL */
    .stApp {{
        background-color: {THEME['bg']};
        color: {THEME['text']};
    }}
    
    /* REMOVER BAGUNÇA */
    .stDeployButton, footer, header, div[data-testid="stToolbar"] {{display: none !important;}}
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] {{
        background-color: {THEME['sidebar']};
        border-right: 1px solid #333;
    }}
    
    /* INPUT DE TEXTO (FIXO NO RODAPÉ) */
    .stChatInput {{
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 20px;
        background-color: {THEME['bg']};
        z-index: 999;
        border-top: 1px solid #333;
    }}
    
    /* --- O MICROFONE PERFEITO --- */
    div[data-testid="stAudioInput"] {{
        position: fixed;
        bottom: 90px;        /* Logo acima da barra de texto */
        right: 20px;         /* Canto direito (padrão mobile) */
        width: 50px !important;
        height: 50px !important;
        z-index: 1000;
    }}
    
    /* Transforma a caixa em uma bolinha */
    div[data-testid="stAudioInput"] > div {{
        border-radius: 50% !important; /* Redondo */
        background-color: {THEME['card']} !important;
        border: 1px solid #444 !important;
        color: {THEME['accent']} !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        padding: 0 !important;
        display: flex;
        justify-content: center;
        align-items: center;
    }}

    /* Esconde qualquer texto para ficar só o ícone */
    div[data-testid="stAudioInput"] label {{
        display: none;
    }}
    
    /* Ajuste de espaçamento para o chat */
    .main .block-container {{
        padding-bottom: 150px;
    }}
    
    /* TEXTO HERO */
    .hero-title {{
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4285F4, #9B72CB, #D96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    
    /* UPLOAD */
    .upload-box {{
        border: 2px dashed #444;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        background-color: {THEME['card']};
    }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. GERENCIAMENTO DE ESTADO
# ==============================================================================
if "sessions" not in st.session_state:
    default_id = str(uuid.uuid4())
    st.session_state.sessions = {
        default_id: {
            "title": "Nova Conversa",
            "history": [],
            "files": [],
            "created_at": datetime.now()
        }
    }
    st.session_state.active_session_id = default_id

if "settings" not in st.session_state:
    st.session_state.settings = {
        "model": "gemini-1.5-flash",
        "temperature": 0.7,
        "system_prompt": "Você é um Assistente Jurídico de Elite."
    }

# ==============================================================================
# 4. FUNÇÕES DO SISTEMA
# ==============================================================================
def get_active_session():
    return st.session_state.sessions[st.session_state.active_session_id]

def create_new_session():
    new_id = str(uuid.uuid4())
    st.session_state.sessions[new_id] = {
        "title": "Nova Conversa",
        "history": [],
        "files": [],
        "created_at": datetime.now()
    }
    st.session_state.active_session_id = new_id
    st.rerun()

def delete_session(sid):
    if len(st.session_state.sessions) > 1:
        del st.session_state.sessions[sid]
        if sid == st.session_state.active_session_id:
            st.session_state.active_session_id = list(st.session_state.sessions.keys())[0]
        st.rerun()

def upload_handler(file_obj):
    try:
        mime = mimetypes.guess_type(file_obj.name)[0] or 'application/octet-stream'
        ext = os.path.splitext(file_obj.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_obj.getvalue())
            tmp_path = tmp.name
        clean_name = "".join([c for c in file_obj.name if c.isalnum() or c in "._- "])
        with st.spinner(f"Processando {clean_name}..."):
            ref = genai.upload_file(path=tmp_path, mime_type=mime, display_name=clean_name)
            while ref.state.name == "PROCESSING":
                time.sleep(1)
                ref = genai.get_file(ref.name)
            return ref
    except Exception as e:
        st.error(f"Erro: {e}")
        return None
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def generate_docx(markdown_text):
    doc = Document()
    doc.add_heading('Relatório Carmélio OS', 0)
    for line in markdown_text.split('\n'):
        if line.strip(): doc.add_paragraph(line)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def run_ai(user_text, audio_data=None):
    session = get_active_session()
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel(st.session_state.settings["model"])
        history = []
        for f in session["files"]:
            history.append({"role": "user", "parts": [f, "Contexto."]})
            history.append({"role": "model", "parts": ["Ok."]})
        if audio_data:
            ref = upload_handler(audio_data)
            if ref:
                history.append({"role": "user", "parts": [ref, "Transcreva e analise."]})
                history.append({"role": "model", "parts": ["Ok."]})
        for m in session["history"]:
            if "🎤" not in str(m["content"]):
                role = "model" if m["role"] == "assistant" else "user"
                history.append({"role": role, "parts": [str(m["content"])]})
        prompt = user_text if user_text else "Analise o conteúdo enviado."
        chat = model.start_chat(history=history)
        response = chat.send_message(prompt)
        session["history"].append({"role": "assistant", "content": response.text})
        if len(session["history"]) <= 2:
            try: session["title"] = model.generate_content(f"Título 3 palavras: {prompt}").text.strip()
            except: pass
    except Exception as e:
        st.error(f"Erro: {e}")

# ==============================================================================
# 5. BARRA LATERAL
# ==============================================================================
def render_sidebar():
    with st.sidebar:
        st.header("Carmélio OS")
        if st.button("➕ Nova Conversa", use_container_width=True, type="primary"):
            create_new_session()
        st.markdown("---")
        with st.expander("📂 Arquivos do Processo", expanded=True):
            session = get_active_session()
            if session["files"]:
                st.info(f"{len(session['files'])} arquivo(s) ativo(s)")
                if st.button("Limpar Arquivos", key="clean_files"):
                    session["files"] = []
                    st.rerun()
            uploaded = st.file_uploader("Adicionar PDF/Áudio", label_visibility="collapsed", key=f"sidebar_up_{st.session_state.active_session_id}")
            if uploaded:
                ref = upload_handler(uploaded)
                if ref:
                    session["files"].append(ref)
                    st.toast("Arquivo salvo na memória!")
                    time.sleep(1)
                    st.rerun()
        st.markdown("---")
        st.markdown("**Histórico**")
        for sid in st.session_state.sessions:
            sess = st.session_state.sessions[sid]
            active = sid == st.session_state.active_session_id
            label = f"{'🟢' if active else '📄'} {sess['title'][:18]}..."
            c1, c2 = st.columns([4,1])
            if c1.button(label, key=sid, use_container_width=True):
                st.session_state.active_session_id = sid
                st.rerun()
            if c2.button("x", key=f"del_{sid}"):
                delete_session(sid)

# ==============================================================================
# 6. TELA PRINCIPAL
# ==============================================================================
def render_main():
    session = get_active_session()
    if not session["history"]:
        st.markdown(f"""
        <div style="text-align: center; margin-top: 15vh;">
            <div class="hero-title">Olá, Arthur</div>
            <p style="color: #888;">Sistema pronto. Carregue um arquivo ou use a voz.</p>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.markdown("<div class='upload-box'>📂 Atalho: Solte seu arquivo aqui</div>", unsafe_allow_html=True)
            center_up = st.file_uploader("Upload Central", label_visibility="collapsed", key="center_up")
            if center_up:
                ref = upload_handler(center_up)
                if ref:
                    session["files"].append(ref)
                    st.success("Arquivo carregado! Pode perguntar abaixo.")
                    time.sleep(1)
                    st.rerun()
        cols = st.columns(3)
        if cols[0].button("📝 Criar Petição", use_container_width=True): handle_input("Crie uma petição inicial.")
        if cols[1].button("🔍 Analisar Riscos", use_container_width=True): handle_input("Analise riscos contratuais.")
        if cols[2].button("📅 Prazos", use_container_width=True): handle_input("Quais os prazos aqui?")
    else:
        chat_container = st.container()
        with chat_container:
            for msg in session["history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant":
                        docx = generate_docx(msg["content"])
                        st.download_button("⬇️ Baixar DOCX", docx, file_name="Carmelio.docx", key=f"d_{hash(msg['content'])}")

# ==============================================================================
# 7. HANDLER DE INPUT (FIXO E DISCRETO)
# ==============================================================================
def handle_input(txt_override=None):
    # A Mágica: O microfone fica flutuando no CSS (bottom right), e o texto fixo no fundo
    audio = st.audio_input("Voz", key="main_mic")
    prompt = st.chat_input("Mensagem para Carmélio OS...")
    
    final_txt = txt_override if txt_override else prompt
    
    if final_txt or audio:
        session = get_active_session()
        disp = final_txt if final_txt else "🎤 [Áudio Enviado]"
        session["history"].append({"role": "user", "content": disp})
        with st.spinner("Processando..."):
            run_ai(final_txt, audio)
        st.rerun()

if __name__ == "__main__":
    render_sidebar()
    render_main()
    handle_input()
