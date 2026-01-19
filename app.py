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
# 1. CONFIGURAÇÃO E DESIGN
# ==============================================================================
st.set_page_config(
    page_title="Carmélio AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded" 
)

THEME = {
    "bg": "#131314",
    "sidebar": "#1E1F20",
    "accent": "#A8C7FA",
    "text": "#E3E3E3",
    "card": "#2D2E2F"
}

st.markdown(f"""
<style>
    /* BASE */
    .stApp {{background-color: {THEME['bg']}; color: {THEME['text']};}}
    .stDeployButton, footer, header, div[data-testid="stToolbar"] {{display: none !important;}}
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] {{background-color: {THEME['sidebar']}; border-right: 1px solid #333;}}
    
    /* INPUT FIXO */
    .stChatInput {{
        position: fixed; bottom: 0; left: 0; right: 0;
        padding: 20px; background-color: {THEME['bg']};
        z-index: 999; border-top: 1px solid #333;
    }}
    
    /* MICROFONE FLUTUANTE (BOLINHA) */
    div[data-testid="stAudioInput"] {{
        position: fixed; bottom: 90px; right: 20px;
        width: 50px !important; height: 50px !important; z-index: 1000;
    }}
    div[data-testid="stAudioInput"] > div {{
        border-radius: 50% !important; background-color: {THEME['card']} !important;
        border: 1px solid #444 !important; color: {THEME['accent']} !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3); padding: 0 !important;
        display: flex; justify-content: center; align-items: center;
    }}
    div[data-testid="stAudioInput"] label {{display: none;}}
    
    /* ESPAÇAMENTO CHAT */
    .main .block-container {{padding-bottom: 150px;}}
    
    /* BOTÕES DE UTILIDADE (CARDS) */
    .utility-card {{
        background-color: {THEME['card']};
        border: 1px solid #444;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: 0.3s;
    }}
    .utility-card:hover {{border-color: {THEME['accent']};}}
    
    /* TÍTULO */
    .hero-title {{
        font-size: 2.5rem; font-weight: 700;
        background: linear-gradient(90deg, #A8C7FA, #F28B82);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. ESTADO
# ==============================================================================
if "sessions" not in st.session_state:
    default_id = str(uuid.uuid4())
    st.session_state.sessions = {
        default_id: {"title": "Nova Tarefa", "history": [], "files": [], "created_at": datetime.now()}
    }
    st.session_state.active_session_id = default_id

# ==============================================================================
# 3. FUNÇÕES TÉCNICAS
# ==============================================================================
def get_session(): return st.session_state.sessions[st.session_state.active_session_id]

def new_session():
    uid = str(uuid.uuid4())
    st.session_state.sessions[uid] = {"title": "Nova Tarefa", "history": [], "files": [], "created_at": datetime.now()}
    st.session_state.active_session_id = uid
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
            tmp.write(file_obj.getvalue()); tpath = tmp.name
        clean_name = "".join([c for c in file_obj.name if c.isalnum() or c in "._- "])
        with st.spinner(f"Processando {clean_name}..."):
            ref = genai.upload_file(path=tpath, mime_type=mime, display_name=clean_name)
            while ref.state.name == "PROCESSING": time.sleep(1); ref = genai.get_file(ref.name)
            return ref
    except Exception as e:
        st.error(f"Erro: {e}"); return None
    finally:
        if os.path.exists(tpath): os.remove(tpath)

def generate_docx(text):
    doc = Document()
    doc.add_heading('Texto Extraído / Transcrição', 0)
    for line in text.split('\n'):
        if line.strip(): doc.add_paragraph(line)
    b = BytesIO(); doc.save(b); b.seek(0)
    return b

def run_ai(prompt, audio=None):
    sess = get_session()
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        hist = []
        # Contexto Arquivos
        for f in sess["files"]:
            hist.append({"role": "user", "parts": [f, "Material de referência."]})
            hist.append({"role": "model", "parts": ["Ok."]})
        
        # Contexto Áudio Novo
        if audio:
            ref = upload_handler(audio)
            if ref:
                hist.append({"role": "user", "parts": [ref, "Transcreva este áudio."]})
                hist.append({"role": "model", "parts": ["Ok."]})

        # Histórico
        for m in sess["history"]:
            if "🎤" not in str(m["content"]):
                role = "model" if m["role"] == "assistant" else "user"
                hist.append({"role": role, "parts": [str(m["content"])]})
        
        # System Prompt Oculto (Focado em Utilitário)
        sys_prompt = "Você é uma ferramenta de produtividade. Se receber áudio, transcreva. Se receber imagem, faça OCR (extraia texto). Se receber documento jurídico, analise. Seja direto."
        
        chat = model.start_chat(history=[{"role":"user", "parts":[sys_prompt]}, {"role":"model", "parts":["Ok."]}] + hist)
        response = chat.send_message(prompt if prompt else "Prossiga.")
        
        sess["history"].append({"role": "assistant", "content": response.text})
        
        # Nomear chat
        if len(sess["history"]) <= 2:
            try: sess["title"] = model.generate_content(f"Título curto 2 palavras para: {prompt}").text.strip()
            except: pass
            
    except Exception as e: st.error(f"Erro: {e}")

# ==============================================================================
# 4. INTERFACE
# ==============================================================================
def sidebar():
    with st.sidebar:
        st.header("Carmélio AI")
        if st.button("➕ Nova Tarefa", type="primary", use_container_width=True): new_session()
        st.markdown("---")
        
        with st.expander("📂 Arquivos / Mídia", expanded=True):
            sess = get_session()
            if sess["files"]:
                st.info(f"{len(sess['files'])} arquivo(s)")
                if st.button("Limpar"): sess["files"] = []; st.rerun()
            up = st.file_uploader("Adicionar", label_visibility="collapsed", key=f"up_{st.session_state.active_session_id}")
            if up:
                ref = upload_handler(up)
                if ref: sess["files"].append(ref); st.rerun()
        
        st.markdown("---")
        st.caption("Histórico")
        for sid in st.session_state.sessions:
            active = sid == st.session_state.active_session_id
            l = f"{'🟢' if active else '📄'} {st.session_state.sessions[sid]['title'][:15]}..."
            c1,c2 = st.columns([4,1])
            if c1.button(l, key=sid): st.session_state.active_session_id = sid; st.rerun()
            if c2.button("x", key=f"d{sid}"): delete_session(sid)

def main():
    sess = get_session()
    
    # TELA DE INÍCIO (ZERO MENSAGENS)
    if not sess["history"]:
        st.markdown(f"""
        <div style="text-align: center; margin-top: 10vh; margin-bottom: 40px;">
            <div class="hero-title">O que vamos converter hoje?</div>
            <p style="color: #888;">Áudio em Texto, Imagem em Word ou Análise Jurídica.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # BOTÕES DE UTILIDADE (ATALHOS MÁGICOS)
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.info("🎙️ **Áudio p/ Texto**")
            st.caption("WhatsApp, Gravações")
            if st.button("Transcrever Áudio", use_container_width=True):
                sess["history"].append({"role": "user", "content": "Transcrever áudio anexado."})
                # Aqui o usuário deve ter anexado o áudio antes ou na hora
                if not sess["files"]: st.warning("Anexe o áudio na barra lateral primeiro!"); return
                run_ai("Transcreva o áudio em anexo integralmente (verbatim). Indique falantes se houver.")
                st.rerun()
                
        with c2:
            st.info("📸 **Imagem p/ Texto**")
            st.caption("Livros, Docs Antigos")
            if st.button("Extrair Texto (OCR)", use_container_width=True):
                sess["history"].append({"role": "user", "content": "Extrair texto da imagem."})
                if not sess["files"]: st.warning("Anexe a imagem/PDF na barra lateral primeiro!"); return
                run_ai("Extraia todo o texto legível desta imagem/documento. Mantenha a formatação original o máximo possível.")
                st.rerun()
                
        with c3:
            st.info("📜 **Certidão/Manuscrito**")
            st.caption("Inteiro Teor, Notas")
            if st.button("Decifrar Documento", use_container_width=True):
                sess["history"].append({"role": "user", "content": "Decifrar certidão/manuscrito."})
                if not sess["files"]: st.warning("Anexe o documento na barra lateral!"); return
                run_ai("Este é um documento difícil de ler (certidão ou manuscrito). Transcreva o conteúdo com precisão jurídica.")
                st.rerun()
                
        st.divider()
        st.caption("Ou use o chat abaixo para conversas livres...")

    # CHAT
    else:
        with st.container():
            for msg in sess["history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant":
                        b = generate_docx(msg["content"])
                        st.download_button("⬇️ Baixar DOCX", b, file_name="Transcricao.docx", key=f"d{hash(msg['content'])}")
            st.markdown("<div style='height: 150px;'></div>", unsafe_allow_html=True)

def inputs():
    aud = st.audio_input("Voz", key="mic")
    txt = st.chat_input("Digite ou grave...")
    if txt or aud:
        sess = get_session()
        d = txt if txt else "🎤 [Comando de Voz]"
        sess["history"].append({"role": "user", "content": d})
        with st.spinner("Processando..."): run_ai(txt, aud)
        st.rerun()

if __name__ == "__main__":
    sidebar()
    main()
    inputs()
