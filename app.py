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
# 1. CONFIGURAÇÃO E CONSTANTES
# ==============================================================================
st.set_page_config(
    page_title="Carmélio AI Enterprise",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cores e Estilos do Design System (Gemini Dark)
THEME = {
    "bg": "#131314",
    "sidebar": "#1E1F20",
    "accent": "#A8C7FA",
    "text": "#E3E3E3",
    "card": "#2D2E2F"
}

# ==============================================================================
# 2. CSS AVANÇADO (ENGINEERING LEVEL)
# ==============================================================================
st.markdown(f"""
<style>
    /* RESET GLOBAL */
    .stApp {{
        background-color: {THEME['bg']};
        color: {THEME['text']};
    }}
    
    /* REMOÇÃO DE BLOATWARE DO STREAMLIT */
    header, footer, .stDeployButton, div[data-testid="stToolbar"] {{display: none !important;}}
    
    /* SIDEBAR CUSTOMIZADA */
    section[data-testid="stSidebar"] {{
        background-color: {THEME['sidebar']};
        border-right: 1px solid #333;
    }}
    
    /* INPUT FIXO NO RODAPÉ (DOCK) */
    .stChatInput {{
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 20px;
        background: linear-gradient(to top, {THEME['bg']} 80%, transparent);
        z-index: 999;
    }}
    
    /* ÁUDIO INPUT FLUTUANTE */
    div[data-testid="stAudioInput"] {{
        position: fixed;
        bottom: 90px;
        right: 40px;
        width: 300px;
        background-color: {THEME['card']};
        border-radius: 12px;
        border: 1px solid #444;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        z-index: 1000;
        transition: all 0.3s ease;
    }}
    div[data-testid="stAudioInput"]:hover {{
        transform: scale(1.02);
        border-color: {THEME['accent']};
    }}
    
    /* TIPOGRAFIA HERO (BOAS VINDAS) */
    .hero-title {{
        font-size: 3.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4285F4, #9B72CB, #D96570);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
    }}
    
    /* CARTÕES DE SUGESTÃO */
    .suggestion-btn {{
        background-color: {THEME['card']};
        border: 1px solid #444;
        border-radius: 12px;
        padding: 15px;
        cursor: pointer;
        transition: 0.2s;
        height: 100%;
    }}
    
    /* MENSAGENS */
    .stChatMessage {{
        background: transparent !important;
        border: none !important;
    }}
    div[data-testid="stChatMessageAvatarUser"] {{
        background-color: {THEME['accent']} !important;
        color: #000 !important;
    }}
    
    /* SCROLLBAR MODERNA */
    ::-webkit-scrollbar {{width: 8px;}}
    ::-webkit-scrollbar-track {{background: {THEME['bg']};}}
    ::-webkit-scrollbar-thumb {{background: #444; border-radius: 4px;}}
    ::-webkit-scrollbar-thumb:hover {{background: #666;}}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. GESTÃO DE ESTADO (STATE MANAGEMENT)
# ==============================================================================
# Inicializa o "Banco de Dados" local da sessão
if "sessions" not in st.session_state:
    # Cria a primeira sessão padrão
    default_id = str(uuid.uuid4())
    st.session_state.sessions = {
        default_id: {
            "title": "Nova Conversa",
            "history": [],
            "files": [], # Suporte a múltiplos arquivos
            "created_at": datetime.now()
        }
    }
    st.session_state.active_session_id = default_id

if "settings" not in st.session_state:
    st.session_state.settings = {
        "model": "gemini-1.5-flash",
        "temperature": 0.7,
        "system_prompt": "Você é um Assistente Jurídico de Elite. Responda com precisão técnica."
    }

# ==============================================================================
# 4. FUNÇÕES DE UTILIDADE (HELPER FUNCTIONS)
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
        # Se apagou a atual, muda para a primeira disponível
        if sid == st.session_state.active_session_id:
            st.session_state.active_session_id = list(st.session_state.sessions.keys())[0]
        st.rerun()

def upload_to_gemini(file_obj):
    """Lida com upload seguro e retorna referência do Gemini"""
    try:
        mime_type = mimetypes.guess_type(file_obj.name)[0] or 'application/octet-stream'
        ext = os.path.splitext(file_obj.name)[1]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_obj.getvalue())
            tmp_path = tmp.name
        
        # Nome sanitizado
        clean_name = "".join([c for c in file_obj.name if c.isalnum() or c in "._- "])
        
        with st.spinner(f"Processando {clean_name}..."):
            ref = genai.upload_file(path=tmp_path, mime_type=mime_type, display_name=clean_name)
            
            # Polling de espera
            while ref.state.name == "PROCESSING":
                time.sleep(1)
                ref = genai.get_file(ref.name)
            
            if ref.state.name == "FAILED":
                st.error("Falha no processamento do Google.")
                return None
                
            return ref
    except Exception as e:
        st.error(f"Erro no upload: {e}")
        return None
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def generate_docx(markdown_text):
    """Motor de exportação para Word"""
    doc = Document()
    doc.add_heading('Relatório Jurídico Carmélio AI', 0)
    doc.add_paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y')}")
    doc.add_paragraph("_" * 50)
    
    # Parser simples de Markdown para Texto
    for line in markdown_text.split('\n'):
        if line.startswith('### '): doc.add_heading(line.replace('#', ''), level=3)
        elif line.startswith('## '): doc.add_heading(line.replace('#', ''), level=2)
        elif line.startswith('# '): doc.add_heading(line.replace('#', ''), level=1)
        elif line.strip(): doc.add_paragraph(line)
        
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==============================================================================
# 5. CORE DA INTELIGÊNCIA ARTIFICIAL
# ==============================================================================
def run_ai_engine(user_input, audio_data=None):
    session = get_active_session()
    
    try:
        # Configuração da API
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        
        # Configuração do Modelo (Baseado nos Settings)
        model_name = st.session_state.settings["model"]
        temp = st.session_state.settings["temperature"]
        
        generation_config = {
            "temperature": temp,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }
        
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=st.session_state.settings["system_prompt"]
        )
        
        history_payload = []
        
        # 1. Injeta Arquivos do Contexto Atual
        if session["files"]:
            for f in session["files"]:
                history_payload.append({"role": "user", "parts": [f, "Arquivo de contexto."]})
                history_payload.append({"role": "model", "parts": ["Arquivo analisado."]})
        
        # 2. Processa Áudio Novo
        if audio_data:
            ref_audio = upload_to_gemini(audio_data)
            if ref_audio:
                history_payload.append({"role": "user", "parts": [ref_audio, "Transcreva e analise este áudio."]})
                history_payload.append({"role": "model", "parts": ["Áudio processado."]})
        
        # 3. Histórico da Conversa
        for msg in session["history"]:
            # Evita mandar msgs de sistema ou placeholders
            if msg["role"] in ["user", "assistant"]:
                role = "model" if msg["role"] == "assistant" else "user"
                # Garante que é string
                content_str = str(msg["content"])
                if "🎤" not in content_str: 
                    history_payload.append({"role": role, "parts": [content_str]})

        # 4. Execução
        prompt_final = user_input if user_input else "Prossiga com a análise."
        
        chat = model.start_chat(history=history_payload)
        response = chat.send_message(prompt_final)
        
        # 5. Salva Resposta
        session["history"].append({"role": "assistant", "content": response.text})
        
        # 6. Gera Título Automático (se for o primeiro turno)
        if len(session["history"]) <= 2:
            try:
                title_gen = model.generate_content(f"Crie um título de 3 palavras para: {prompt_final}")
                session["title"] = title_gen.text.strip()
            except: pass
            
    except Exception as e:
        st.error(f"Erro Crítico na IA: {e}")
        session["history"].append({"role": "assistant", "content": f"⚠️ Erro de execução: {str(e)}"})

# ==============================================================================
# 6. INTERFACE: BARRA LATERAL (SIDEBAR)
# ==============================================================================
def render_sidebar():
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Google_Gemini_logo.svg/2560px-Google_Gemini_logo.svg.png", width=120)
        st.markdown("### Carmélio OS `v13.0`")
        
        # Botão Nova Conversa
        if st.button("➕ Nova Conversa", use_container_width=True, type="primary"):
            create_new_session()
            
        st.markdown("---")
        
        # Histórico de Conversas
        st.markdown("**🗂️ Histórico Recente**")
        # Ordena por mais recente
        sorted_ids = sorted(st.session_state.sessions.keys(), key=lambda k: st.session_state.sessions[k]['created_at'], reverse=True)
        
        for sid in sorted_ids:
            sess = st.session_state.sessions[sid]
            # Estilo visual para sessão ativa
            is_active = sid == st.session_state.active_session_id
            label = f"{'🟢' if is_active else '📄'} {sess['title'][:20]}..."
            
            c1, c2 = st.columns([5, 1])
            with c1:
                if st.button(label, key=f"sel_{sid}", use_container_width=True):
                    st.session_state.active_session_id = sid
                    st.rerun()
            with c2:
                if st.button("x", key=f"del_{sid}"):
                    delete_session(sid)
                    
        st.markdown("---")
        
        # Área de Configurações Avançadas (Expandida)
        with st.expander("⚙️ Configurações & IA", expanded=False):
            st.session_state.settings["temperature"] = st.slider("Criatividade (Temp)", 0.0, 1.0, 0.7)
            st.session_state.settings["model"] = st.selectbox("Modelo", ["gemini-1.5-flash", "gemini-1.5-pro"])
            st.text_area("System Prompt (Persona)", value=st.session_state.settings["system_prompt"], key="sys_prompt_input")
            
        # Área de Upload de Contexto
        with st.expander("📂 Contexto da Sessão", expanded=True):
            active_s = get_active_session()
            if active_s["files"]:
                st.caption(f"{len(active_s['files'])} arquivo(s) na memória.")
                if st.button("Limpar Arquivos"):
                    active_s["files"] = []
                    st.rerun()
            
            new_file = st.file_uploader("Adicionar", label_visibility="collapsed", key=f"up_{st.session_state.active_session_id}")
            if new_file:
                ref = upload_to_gemini(new_file)
                if ref:
                    active_s["files"].append(ref)
                    st.toast("Arquivo indexado com sucesso!")
                    time.sleep(1)
                    st.rerun()

# ==============================================================================
# 7. INTERFACE: ÁREA PRINCIPAL
# ==============================================================================
def render_main():
    session = get_active_session()
    
    # Tela de Boas Vindas (Se vazio)
    if not session["history"]:
        st.markdown(f"""
        <div class="hero-container" style="text-align: center; margin-top: 15vh;">
            <div class="hero-title">Olá, Arthur</div>
            <p style="font-size: 1.2rem; color: #888;">Seu sistema jurídico de alta performance está pronto.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sugestões Rápidas
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📝 Redigir Petição Inicial", use_container_width=True):
                handle_input("Redija uma petição inicial padrão para este caso.")
        with c2:
            if st.button("🔍 Analisar Contrato", use_container_width=True):
                handle_input("Analise o contrato em anexo e aponte riscos.")
        with c3:
            if st.button("📅 Resumo de Prazos", use_container_width=True):
                handle_input("Faça um quadro com todos os prazos processuais.")
                
    else:
        # Renderização do Chat
        # Padding inferior para não bater no input fixo
        chat_container = st.container()
        with chat_container:
            for msg in session["history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
                    # Funcionalidades Extras para Respostas da IA
                    if msg["role"] == "assistant":
                        col_a, col_b = st.columns([1, 10])
                        with col_a:
                            # Botão de Exportação
                            docx = generate_docx(msg["content"])
                            st.download_button("💾 DOCX", docx, file_name="Carmelio_Export.docx", key=f"d_{hash(msg['content'])}")
            
            st.markdown("<div style='height: 150px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 8. HANDLER DE INPUT (FIXO NO RODAPÉ)
# ==============================================================================
def handle_input(text_override=None):
    # Verifica input de texto ou áudio
    prompt = st.chat_input("Digite sua mensagem para o Carmélio OS...")
    
    # Widget de Áudio Flutuante
    audio_blob = st.audio_input("Falar", key=f"aud_{st.session_state.active_session_id}")
    
    # Determina qual input usar
    final_input = text_override if text_override else prompt
    
    if final_input or audio_blob:
        session = get_active_session()
        
        # Exibe mensagem do usuário
        user_msg = final_input if final_input else "🎤 [Áudio Enviado]"
        session["history"].append({"role": "user", "content": user_msg})
        
        # Spinner e Chamada IA
        with st.spinner("🧠 Carmélio Neural Engine processando..."):
            run_ai_engine(final_input, audio_blob)
        
        st.rerun()

# ==============================================================================
# 9. EXECUTOR
# ==============================================================================
if __name__ == "__main__":
    render_sidebar()
    render_main()
    # Chama o input handler por último para garantir que fique no fim da renderização
    handle_input()
