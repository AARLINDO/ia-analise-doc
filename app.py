import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
import mimetypes
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(
    page_title="Carmélio AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stAudioInput {border: 2px solid #4CAF50; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# --- 2. ESTADO ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "chats" not in st.session_state:
    st.session_state.chats = {"chat_1": {"title": "Nova Conversa", "history": [], "file": None}}
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = "chat_1"
if "tom" not in st.session_state: st.session_state.tom = "Formal (Jurídico)"

# --- 3. FUNÇÕES ---
def gerar_word(texto):
    try:
        doc = Document()
        doc.add_heading('Análise Carmélio AI', 0)
        doc.add_paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        doc.add_paragraph('---')
        doc.add_paragraph(texto)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except: return None

def upload_seguro(up):
    try:
        mime = mimetypes.guess_type(up.name)[0] or 'application/octet-stream'
        ext = os.path.splitext(up.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(up.getvalue()); tmp_path = tmp.name
        
        # Nome limpo para o Google não reclamar
        ref = genai.upload_file(path=tmp_path, mime_type=mime, display_name="Arquivo_Analise")
        
        timeout = 60
        start = time.time()
        while ref.state.name == "PROCESSING":
            if time.time() - start > timeout: raise Exception("Tempo limite excedido")
            time.sleep(1); ref = genai.get_file(ref.name)
            
        os.remove(tmp_path)
        if ref.state.name == "FAILED": raise Exception("Falha no processamento do Google")
        return ref
    except Exception as e:
        st.error(f"Erro upload: {e}"); return None

def login():
    c1,c2,c3 = st.columns([1,2,1])
    with c2:
        st.title("⚖️ Carmélio AI")
        u = st.text_input("Usuário"); s = st.text_input("Senha", type="password")
        if st.button("Entrar", type="primary"):
            creds = st.secrets.get("passwords", {})
            if u in creds and str(creds[u]) == str(s):
                st.session_state.logged_in = True; st.session_state.username = u; st.rerun()
            else: st.error("Senha incorreta")

def sidebar():
    with st.sidebar:
        st.header(f"Olá, {st.session_state.username}")
        st.session_state.tom = st.selectbox("Tom da Resposta:", ["Formal (Jurídico)", "Didático (Cliente)", "Executivo (Resumo)"])
        st.divider()
        if st.button("➕ Nova Conversa", type="primary"):
            nid = f"c_{int(time.time())}"
            st.session_state.chats[nid] = {"title": "Nova Conversa", "history": [], "file": None}
            st.session_state.current_chat_id = nid; st.rerun()
        
        for cid in list(st.session_state.chats.keys())[::-1]:
            c = st.session_state.chats[cid]
            if st.button(f"📂 {c['title'][:18]}...", key=cid):
                st.session_state.current_chat_id = cid; st.rerun()
        st.divider(); 
        if st.button("Sair"): st.session_state.logged_in = False; st.rerun()

def processar(prompt, audio, chat_data, auto_start=False):
    with st.spinner("🤖 Analisando..."):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            hist = []
            
            # Contexto
            if chat_data["file"]:
                hist.append({"role": "user", "parts": [chat_data["file"], "Analise este arquivo."]})
                hist.append({"role": "model", "parts": ["Arquivo recebido."]})
            
            if audio:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as t:
                    t.write(audio.getvalue()); tp = t.name
                ref = genai.upload_file(path=tp, mime_type="audio/wav")
                while ref.state.name == "PROCESSING": time.sleep(1); ref = genai.get_file(ref.name)
                hist.append({"role": "user", "parts": [ref, "Transcreva/Analise o áudio."]})
                hist.append({"role": "model", "parts": ["Áudio recebido."]})
                os.remove(tp)

            # Persona
            sys = f"Você é Carmélio AI. Tom: {st.session_state.tom}. Responda em Markdown claro."
            hist.append({"role": "user", "parts": [sys]})
            hist.append({"role": "model", "parts": ["Entendido."]})

            # Histórico anterior
            for m in chat_data["history"]:
                r = "model" if m["role"] == "assistant" else "user"
                hist.append({"role": r, "parts": [m["content"]]})
            
            final_p = prompt if prompt else "Faça um Resumo Executivo detalhado deste arquivo."
            
            chat = model.start_chat(history=hist)
            resp = chat.send_message(final_p)
            
            chat_data["history"].append({"role": "assistant", "content": resp.text})
            
            if chat_data["title"] == "Nova Conversa":
                try: chat_data["title"] = model.generate_content(f"Título curto 3 palavras: {final_p}").text.strip()
                except: pass
                
        except Exception as e: st.error(f"Erro IA: {e}")

def app():
    try: genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except: st.error("Erro API"); st.stop()
    
    cd = st.session_state.chats[st.session_state.current_chat_id]
    st.title(cd['title'])

    # --- UPLOAD ---
    if not cd["file"]:
        with st.expander("📎 Carregar Arquivo (Arraste aqui)", expanded=True):
            up = st.file_uploader("PDF, Áudio, Imagem", key=f"u_{st.session_state.current_chat_id}")
            if up:
                with st.spinner("Processando..."):
                    ref = upload_seguro(up)
                    if ref:
                        cd["file"] = ref
                        # Não adicionamos mensagem de texto aqui para não poluir
                        # Chamamos a IA direto para já dar o resumo!
                        processar("Faça um resumo executivo inicial deste documento, destacando pontos chaves.", None, cd, auto_start=True)
                        st.rerun()
    else:
        st.info("Arquivo em análise. Pergunte mais abaixo ou veja o resumo.")

    # --- CHAT ---
    for msg in cd["history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # LÓGICA CORRIGIDA DO BOTÃO WORD
            # Só mostra o botão se for resposta da IA (assistant) E se o texto for longo (> 200 caracteres)
            if msg["role"] == "assistant" and len(msg["content"]) > 200:
                docx = gerar_word(msg["content"])
                if docx:
                    st.download_button("📄 Baixar Resposta em Word", docx, 
                                     file_name=f"Analise_{datetime.now().strftime('%H%M')}.docx",
                                     key=f"d_{hash(msg['content'])}")

    # --- INPUT ---
    st.divider()
    ca, ct = st.columns([1,5])
    with ca: aud = st.audio_input("Voz", key=f"a_{st.session_state.current_chat_id}")
    with ct: txt = st.chat_input("Pergunte sobre o documento...")

    if aud or txt:
        disp = txt if txt else "🎤 (Áudio enviado)"
        cd["history"].append({"role": "user", "content": disp})
        processar(txt, aud, cd)
        st.rerun()

if not st.session_state.logged_in: login()
else: sidebar(); app()
