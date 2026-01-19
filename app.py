import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Carmélio AI - Voice Edition",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    /* Destaque para o Gravador */
    .stAudioInput {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 10px;
        background-color: #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SETUP DE ESTADO ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "chats" not in st.session_state:
    st.session_state.chats = {"chat_1": {"title": "Nova Conversa", "history": [], "file": None, "file_type": None}}
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = "chat_1"
if "mode" not in st.session_state: st.session_state.mode = "Análise de Arquivos"

# --- 3. FUNÇÕES UTILITÁRIAS ---
def gerar_word(texto):
    doc = Document()
    doc.add_heading('Transcrição/Análise Carmélio AI', 0)
    doc.add_paragraph(texto)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def login():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("⚖️ Carmélio AI Voice")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            creds = st.secrets.get("passwords", {})
            if usuario in creds and creds[usuario] == senha:
                st.session_state.logged_in = True
                st.session_state.username = usuario
                st.rerun()
            else:
                st.error("Erro de acesso.")

def sidebar_menu():
    with st.sidebar:
        st.write(f"Olá, **{st.session_state.username}**")
        st.session_state.mode = st.radio("Modo:", ["Análise de Arquivos", "Chat Livre"])
        
        st.divider()
        if st.button("➕ Nova Conversa"):
            new_id = f"chat_{len(st.session_state.chats)+1}"
            st.session_state.chats[new_id] = {"title": f"Chat {len(st.session_state.chats)+1}", "history": [], "file": None, "file_type": None}
            st.session_state.current_chat_id = new_id
            st.rerun()
            
        for cid, cdata in list(st.session_state.chats.items())[::-1]:
            label = f"📂 {cdata['title']}" if cid != st.session_state.current_chat_id else f"📂 {cdata['title']} (Atual)"
            if st.button(label, key=cid):
                st.session_state.current_chat_id = cid
                st.rerun()
        
        st.divider()
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

def processar_ia(prompt_texto, audio_mic, chat_data):
    # Função Central de Inteligência
    with st.spinner("Ouvindo e Analisando..."):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash-latest")
            history_api = []
            
            # 1. Se tiver Arquivo anexado (PDF/IMG/MP3 upload)
            if chat_data["file"]:
                history_api.append({"role": "user", "parts": [chat_data["file"], "Considere este arquivo anexo."]})
                history_api.append({"role": "model", "parts": ["Arquivo recebido."]})

            # 2. Se tiver Áudio do Microfone (Novo!)
            if audio_mic:
                # Salva o áudio do mic temporariamente
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_mic:
                    tmp_mic.write(audio_mic.getvalue())
                    tmp_mic_path = tmp_mic.name
                
                # Sobe pro Google
                mic_ref = genai.upload_file(tmp_mic_path)
                while mic_ref.state.name == "PROCESSING": time.sleep(1); mic_ref = genai.get_file(mic_ref.name)
                
                # Adiciona instrução de voz
                history_api.append({"role": "user", "parts": [mic_ref, "Este é um áudio da minha voz. Transcreva e execute o comando falado."]})
                history_api.append({"role": "model", "parts": ["Entendido, ouvi seu áudio."]})
                os.remove(tmp_mic_path)

            # 3. Adiciona o Texto Digitado (se houver)
            prompt_final = prompt_texto if prompt_texto else "Analise o conteúdo enviado (áudio ou arquivo)."

            # Recupera histórico do chat
            for m in chat_data["history"]:
                role = "model" if m["role"] == "assistant" else "user"
                history_api.append({"role": role, "parts": [m["content"]]})
            
            # Envia tudo
            chat = model.start_chat(history=history_api)
            response = chat.send_message(prompt_final)
            
            # Salva resposta
            chat_data["history"].append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Erro: {e}")

def main_app():
    try: genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except: st.error("Erro API"); st.stop()
    
    chat_data = st.session_state.chats[st.session_state.current_chat_id]
    st.subheader(f"🎙️ {chat_data['title']}")

    # --- ÁREA DE UPLOAD (Arquivos Pesados) ---
    if st.session_state.mode == "Análise de Arquivos" and not chat_data["file"]:
        up = st.file_uploader("Anexar Documento ou Áudio (Upload)", type=["pdf", "jpg", "png", "mp3", "m4a"], key=f"u_{st.session_state.current_chat_id}")
        if up:
            with st.spinner("Subindo arquivo..."):
                ext = os.path.splitext(up.name)[1] or ".tmp"
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    tmp.write(up.getvalue()); tmp_path = tmp.name
                ref = genai.upload_file(tmp_path)
                while ref.state.name == "PROCESSING": time.sleep(1); ref = genai.get_file(ref.name)
                chat_data["file"] = ref
                chat_data["history"].append({"role": "assistant", "content": "Arquivo anexado com sucesso."})
                os.remove(tmp_path); st.rerun()

    # --- EXIBIÇÃO DO CHAT ---
    for msg in chat_data["history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and len(msg["content"]) > 50:
                data = gerar_word(msg["content"])
                st.download_button("📄 Baixar Word", data, file_name="Carmelio_AI.docx", key=f"d_{hash(msg['content'])}")

    # --- ÁREA DE COMANDO (HÍBRIDA: VOZ + TEXTO) ---
    st.divider()
    col_mic, col_text = st.columns([1, 4])
    
    with col_mic:
        # O Novo Gravador Nativo do Streamlit
        audio_mic = st.audio_input("Gravar", key=f"mic_{st.session_state.current_chat_id}")

    with col_text:
        texto_input = st.chat_input("Digite ou grave um comando...")

    # Gatilho: Se gravou áudio OU digitou texto
    if audio_mic or texto_input:
        # Só processa se for um evento novo (para evitar loop)
        # Na prática, o audio_input mantem o estado, então checamos se já não foi processado
        # Mas para simplificar aqui, vamos processar direto.
        
        # Adiciona a mensagem do usuário no visual
        msg_user = ""
        if audio_mic: msg_user += "🎤 [Áudio de Voz Enviado] "
        if texto_input: msg_user += texto_input
        
        chat_data["history"].append({"role": "user", "content": msg_user})
        st.rerun() # Atualiza tela para mostrar msg do user antes de processar

    # Processamento Pós-Rerun (Gambiarra inteligente do Streamlit)
    if chat_data["history"] and chat_data["history"][-1]["role"] == "user":
        # Se a última msg foi do usuário e a IA ainda não respondeu...
        last_msg = chat_data["history"][-1]["content"]
        
        # Se a última ação foi mandar áudio ou texto, chamamos a IA
        # Nota: Precisamos passar o objeto audio_mic de novo se ele ainda estiver ativo
        processar_ia(texto_input, audio_mic, chat_data)
        st.rerun()

if not st.session_state.logged_in:
    login()
else:
    sidebar_menu()
    main_app()
