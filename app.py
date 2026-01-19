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
    page_title="Carmélio AI - Legal Suite",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    
    /* Estilo dos Cartões de Sugestão */
    .suggestion-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #e0e0e0;
        cursor: pointer;
        transition: 0.3s;
    }
    .suggestion-card:hover {
        background-color: #e0e0e0;
        border-color: #d0d0d0;
    }
    
    /* Gravador */
    .stAudioInput {
        border: 2px solid #4CAF50; /* Borda verde para destacar */
        border-radius: 10px;
        background-color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SETUP DE ESTADO ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "chats" not in st.session_state:
    st.session_state.chats = {"chat_1": {"title": "Nova Conversa", "history": [], "file": None}}
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = "chat_1"

# --- 3. FUNÇÕES ---
def gerar_word(texto):
    doc = Document()
    doc.add_heading('Relatório Carmélio AI', 0)
    doc.add_paragraph(texto)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def login():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("⚖️ Carmélio AI")
        st.caption("Acesso Restrito - Voice Edition")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary"):
            creds = st.secrets.get("passwords", {})
            if usuario in creds and creds[usuario] == senha:
                st.session_state.logged_in = True
                st.session_state.username = usuario
                st.rerun()
            else:
                st.error("Acesso Negado")

def sidebar_menu():
    with st.sidebar:
        st.header(f"Olá, {st.session_state.username}")
        
        # --- NOVO: SELETOR DE PERSONALIDADE ---
        st.markdown("### 🎭 Tom da IA")
        st.session_state.tom = st.selectbox(
            "Como devo responder?",
            ["Formal (Jurídico)", "Didático (Para Cliente)", "Agressivo (Defesa)", "Executivo (Resumo)"]
        )
        
        st.divider()
        st.markdown("### 🗂️ Chats")
        if st.button("➕ Nova Conversa"):
            new_id = f"chat_{len(st.session_state.chats)+1}"
            st.session_state.chats[new_id] = {"title": "Nova Conversa", "history": [], "file": None}
            st.session_state.current_chat_id = new_id
            st.rerun()
            
        for cid in list(st.session_state.chats.keys())[::-1]:
            cdata = st.session_state.chats[cid]
            label = f"📂 {cdata['title']}" if cid != st.session_state.current_chat_id else f"📂 {cdata['title']} (Atual)"
            if st.button(label, key=cid):
                st.session_state.current_chat_id = cid
                st.rerun()
                
        st.divider()
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

def processar_ia(prompt, audio, chat_data):
    with st.spinner("🤖 Processando..."):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash-latest")
            history_api = []
            
            # Personalidade no System Prompt
            tom_instruction = ""
            if st.session_state.tom == "Formal (Jurídico)":
                tom_instruction = "Use linguagem jurídica culta, cite artigos de lei e seja impessoal."
            elif st.session_state.tom == "Didático (Para Cliente)":
                tom_instruction = "Explique como se fosse para uma criança de 10 anos. Evite 'juridiquês'. Use metáforas."
            elif st.session_state.tom == "Agressivo (Defesa)":
                tom_instruction = "Busque falhas, nulidades e argumentos fortes para defesa. Seja incisivo."
            
            system_msg = f"Você é o Carmélio AI. {tom_instruction} Responda sempre em Português BR."
            
            # Monta contexto
            if chat_data["file"]:
                history_api.append({"role": "user", "parts": [chat_data["file"], "Considere este arquivo."]})
                history_api.append({"role": "model", "parts": ["Ok."]})
            
            if audio:
                # Processa áudio novo
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    tmp.write(audio.getvalue()); tmp_path = tmp.name
                ref = genai.upload_file(tmp_path)
                while ref.state.name == "PROCESSING": time.sleep(1); ref = genai.get_file(ref.name)
                history_api.append({"role": "user", "parts": [ref, "Transcreva e analise este áudio."]})
                history_api.append({"role": "model", "parts": ["Áudio recebido."]})
                os.remove(tmp_path)

            history_api.append({"role": "user", "parts": [system_msg]}) # Reforça a personalidade
            history_api.append({"role": "model", "parts": ["Entendido."]})

            # Histórico antigo
            for m in chat_data["history"]:
                role = "model" if m["role"] == "assistant" else "user"
                history_api.append({"role": role, "parts": [m["content"]]})
            
            # Prompt final
            if not prompt: prompt = "Prossiga com a análise."
            
            chat = model.start_chat(history=history_api)
            response = chat.send_message(prompt)
            
            # Salva
            chat_data["history"].append({"role": "assistant", "content": response.text})
            
            # Atualiza título se for conversa nova
            if chat_data["title"] == "Nova Conversa":
                resumo_titulo = model.generate_content(f"Resuma em 3 palavras para um título: {prompt}")
                chat_data["title"] = resumo_titulo.text.strip()
                
        except Exception as e:
            st.error(f"Erro: {e}")

def main_app():
    try: genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except: st.error("Erro API"); st.stop()
    
    chat_data = st.session_state.chats[st.session_state.current_chat_id]
    st.title(f"{chat_data['title']}")

    # --- UPLOAD ---
    if not chat_data["file"]:
        with st.expander("📎 Anexar Arquivo (PDF/Áudio/Imagem)", expanded=False):
            up = st.file_uploader("Selecione arquivo", type=["pdf","jpg","png","mp3","m4a"], key=f"u_{st.session_state.current_chat_id}")
            if up:
                with st.spinner("Enviando..."):
                    ext = os.path.splitext(up.name)[1] or ".tmp"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                        tmp.write(up.getvalue()); tmp_path = tmp.name
                    ref = genai.upload_file(tmp_path)
                    while ref.state.name == "PROCESSING": time.sleep(1); ref = genai.get_file(ref.name)
                    chat_data["file"] = ref
                    chat_data["history"].append({"role": "assistant", "content": f"Arquivo {up.name} anexado."})
                    os.remove(tmp_path); st.rerun()
    else:
        st.info("📎 Arquivo Anexado e Pronto para Análise.")

    # --- HISTÓRICO ---
    if not chat_data["history"]:
        # TELA DE BOAS VINDAS (VAZIA)
        st.markdown("### Como posso ajudar você hoje?")
        c1, c2, c3 = st.columns(3)
        if c1.button("📝 Redigir Petição"):
            processar_ia("Redija um esboço de petição inicial sobre...", None, chat_data); st.rerun()
        if c2.button("🔍 Analisar Riscos"):
            processar_ia("Quais são os riscos jurídicos deste caso?", None, chat_data); st.rerun()
        if c3.button("📧 E-mail Cliente"):
            processar_ia("Escreva um e-mail formal explicando a situação...", None, chat_data); st.rerun()
    
    for msg in chat_data["history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and len(msg["content"]) > 50:
                data = gerar_word(msg["content"])
                st.download_button("⬇️ Word", data, file_name="CarmelioAI.docx", key=f"d_{hash(msg['content'])}")

    # --- INPUT ---
    st.divider()
    col_mic, col_txt = st.columns([1,5])
    with col_mic:
        audio = st.audio_input("Falar", key=f"a_{st.session_state.current_chat_id}")
    with col_txt:
        txt = st.chat_input("Digite sua mensagem...")

    if audio or txt:
        # User msg
        disp_txt = txt if txt else "🎤 (Áudio Enviado)"
        chat_data["history"].append({"role": "user", "content": disp_txt})
        
        # Chama IA
        processar_ia(txt, audio, chat_data)
        st.rerun()

if not st.session_state.logged_in: login()
else: sidebar_menu(); main_app()
