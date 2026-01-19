import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
import mimetypes
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIGURAÇÃO E ESTILO ---
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
    
    /* Cards de Sugestão */
    .suggestion-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        text-align: center;
        font-size: 0.9rem;
        transition: 0.3s;
        cursor: pointer;
    }
    .suggestion-card:hover {
        background-color: #e9ecef;
        border-color: #adb5bd;
    }
    
    /* Estilo do Chat */
    .stChatMessage {
        border: 1px solid #f0f2f6;
        border-radius: 12px;
    }
    
    /* Status de Sucesso/Erro */
    .stAlert {
        padding: 0.5rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. INICIALIZAÇÃO DE VARIÁVEIS SEGURAS ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "chats" not in st.session_state:
    st.session_state.chats = {"chat_1": {"title": "Nova Conversa", "history": [], "file": None}}
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = "chat_1"
if "tom" not in st.session_state: st.session_state.tom = "Formal (Jurídico)"

# --- 3. FUNÇÕES DE UTILIDADE E SEGURANÇA ---

def limpar_nome_arquivo(nome_original):
    """Remove caracteres perigosos que quebram o Google API"""
    nome_seguro = "".join(c for c in nome_original if c.isalnum() or c in "._- ")
    return nome_seguro[:50] # Limita tamanho para evitar erro de buffer

def gerar_word(texto):
    """Gera o arquivo Word de forma segura"""
    try:
        doc = Document()
        doc.add_heading('Relatório Carmélio AI', 0)
        doc.add_paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y')}")
        doc.add_paragraph('---')
        doc.add_paragraph(texto)
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Erro ao gerar Word: {e}")
        return None

def upload_seguro_google(uploaded_file):
    """Gerencia o upload com retries, timeout e MimeType correto"""
    try:
        # 1. Identificar Mime Type Corretamente
        mime_type, _ = mimetypes.guess_type(uploaded_file.name)
        if not mime_type:
            # Fallback para tipos comuns se a detecção falhar
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            if ext == '.pdf': mime_type = 'application/pdf'
            elif ext in ['.mp3', '.wav']: mime_type = 'audio/mpeg'
            elif ext in ['.jpg', '.jpeg', '.png']: mime_type = 'image/jpeg'
            else: mime_type = 'application/octet-stream'

        # 2. Salvar Temporário
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        # 3. Upload com Nome Sanitizado
        nome_limpo = limpar_nome_arquivo(uploaded_file.name)
        file_ref = genai.upload_file(
            path=tmp_path,
            mime_type=mime_type,
            display_name=nome_limpo
        )

        # 4. Aguardar Processamento (Timeout de 60s)
        timeout = 60 
        start_time = time.time()
        
        while file_ref.state.name == "PROCESSING":
            if time.time() - start_time > timeout:
                raise TimeoutError("O Google demorou demais para processar este arquivo.")
            time.sleep(2)
            file_ref = genai.get_file(file_ref.name)
            
        if file_ref.state.name == "FAILED":
            raise ValueError("O Google rejeitou o arquivo (Formato inválido ou corrompido).")

        # Limpeza local
        os.remove(tmp_path)
        return file_ref

    except Exception as e:
        if os.path.exists(tmp_path): os.remove(tmp_path)
        raise e

# --- 4. FLUXO DE LOGIN ---
def login():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>⚖️ Carmélio AI</h1>", unsafe_allow_html=True)
        st.info("Sistema Jurídico Multimodal | v8.0 Stable")
        
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Acessar Sistema", type="primary"):
            creds = st.secrets.get("passwords", {})
            # Verifica se credenciais existem e batem
            if usuario in creds and str(creds[usuario]) == str(senha):
                st.session_state.logged_in = True
                st.session_state.username = usuario
                st.toast("Acesso Permitido!", icon="✅")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Credenciais inválidas. Tente novamente.")

# --- 5. INTERFACE PRINCIPAL ---
def sidebar_menu():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        
        st.markdown("---")
        st.markdown("**Configuração da IA**")
        st.session_state.tom = st.selectbox(
            "Personalidade:",
            ["Formal (Jurídico)", "Didático (Cliente)", "Incisivo (Defesa)", "Executivo (Resumo)"]
        )
        
        st.markdown("---")
        c_new, c_del = st.columns([4,1])
        if c_new.button("➕ Nova Conversa", type="primary"):
            new_id = f"chat_{int(time.time())}" # ID único baseado em tempo
            st.session_state.chats[new_id] = {"title": "Nova Conversa", "history": [], "file": None}
            st.session_state.current_chat_id = new_id
            st.rerun()

        st.markdown("### Histórico")
        # Lista chats (mais recentes primeiro)
        for cid in list(st.session_state.chats.keys())[::-1]:
            cdata = st.session_state.chats[cid]
            label = f"📂 {cdata['title'][:20]}..."
            
            # Destaque visual para chat atual
            if cid == st.session_state.current_chat_id:
                st.markdown(f"**👉 {cdata['title']}**")
            else:
                if st.button(label, key=cid):
                    st.session_state.current_chat_id = cid
                    st.rerun()
        
        st.markdown("---")
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

def processar_ia(prompt, audio_file, chat_data):
    """Núcleo de Inteligência da Aplicação"""
    with st.spinner("🤖 Analisando dados..."):
        try:
            # Configuração do Modelo (Versão Estável)
            model = genai.GenerativeModel("gemini-1.5-flash")
            history_api = []
            
            # Instrução de Sistema (Persona)
            instrucoes = {
                "Formal (Jurídico)": "Use linguagem técnica, cite leis (CF/88, CPC, CC) e mantenha tom impessoal.",
                "Didático (Cliente)": "Explique de forma simples, evite latim, use analogias. Foco no entendimento do leigo.",
                "Incisivo (Defesa)": "Foque em teses de nulidade, prescrição e defesa do réu. Seja argumentativo.",
                "Executivo (Resumo)": "Use tópicos (bullet points). Seja extremamente breve e direto. Foco em datas e valores."
            }
            system_msg = f"Você é o Carmélio AI. {instrucoes.get(st.session_state.tom, '')} Responda em Português."

            # Montagem do Contexto (Arquivo + Voz + Texto)
            # 1. Arquivo (se houver)
            if chat_data["file"]:
                history_api.append({"role": "user", "parts": [chat_data["file"], "Analise este documento/arquivo em anexo."]})
                history_api.append({"role": "model", "parts": ["Arquivo recebido e analisado."]})
            
            # 2. Áudio do Microfone (se houver)
            if audio_file:
                # Upload do áudio do mic
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    tmp.write(audio_file.getvalue()); tmp_path = tmp.name
                
                mic_ref = genai.upload_file(path=tmp_path, mime_type="audio/wav")
                # Espera processar
                while mic_ref.state.name == "PROCESSING": time.sleep(1); mic_ref = genai.get_file(mic_ref.name)
                
                history_api.append({"role": "user", "parts": [mic_ref, "Transcreva e execute o comando deste áudio."]})
                history_api.append({"role": "model", "parts": ["Áudio de voz recebido."]})
                os.remove(tmp_path)

            # 3. Instrução de Sistema + Prompt Texto
            history_api.append({"role": "user", "parts": [system_msg]})
            history_api.append({"role": "model", "parts": ["Entendido."]})

            # 4. Histórico da Conversa
            for m in chat_data["history"]:
                role = "model" if m["role"] == "assistant" else "user"
                history_api.append({"role": role, "parts": [m["content"]]})
            
            # Execução
            final_prompt = prompt if prompt else "Prossiga com a análise do que foi enviado."
            
            chat = model.start_chat(history=history_api)
            response = chat.send_message(final_prompt)
            
            # Salvar e Renomear Chat se for novo
            chat_data["history"].append({"role": "assistant", "content": response.text})
            
            if chat_data["title"] == "Nova Conversa":
                # Tenta dar um nome melhor baseado no contexto
                try:
                    name_response = model.generate_content(f"Crie um título curto de 3 palavras para este assunto: {final_prompt}")
                    chat_data["title"] = name_response.text.strip()
                except:
                    pass # Se falhar, mantém "Nova Conversa"

        except Exception as e:
            st.error(f"Erro na IA: {e}")
            st.error("Dica: Verifique se o arquivo não é muito grande ou se sua chave de API é válida.")

def main_app():
    # Setup da API Seguro
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    except Exception as e:
        st.error("Erro Crítico: Chave de API não configurada nos Secrets.")
        st.stop()
    
    # Recupera chat atual
    chat_data = st.session_state.chats[st.session_state.current_chat_id]
    st.title(f"{chat_data['title']}")

    # --- ÁREA DE UPLOAD (Expansível) ---
    with st.expander("📎 Arquivos (PDF, Áudio, Imagens)", expanded=not chat_data["file"]):
        if not chat_data["file"]:
            up = st.file_uploader(
                "Arraste seu arquivo aqui", 
                type=["pdf", "jpg", "png", "jpeg", "mp3", "wav", "m4a", "ogg"],
                key=f"upl_{st.session_state.current_chat_id}"
            )
            if up:
                with st.spinner("Enviando para servidor seguro (Sanitizando)..."):
                    try:
                        file_ref = upload_seguro_google(up)
                        chat_data["file"] = file_ref
                        chat_data["history"].append({"role": "assistant", "content": f"✅ Arquivo **{up.name}** processado e pronto para análise."})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Falha no Upload: {e}")
        else:
            st.success(f"Arquivo carregado: {chat_data['file'].display_name}")
            if st.button("🗑️ Remover Arquivo"):
                chat_data["file"] = None
                st.rerun()

    # --- SUGESTÕES (ONBOARDING) ---
    if not chat_data["history"] and not chat_data["file"]:
        st.markdown("#### Comece rápido:")
        c1, c2, c3 = st.columns(3)
        if c1.button("📝 Redigir Petição"): processar_ia("Escreva uma petição inicial sobre...", None, chat_data); st.rerun()
        if c2.button("📅 Calcular Prazos"): processar_ia("Quais são os prazos processuais para...", None, chat_data); st.rerun()
        if c3.button("🔍 Pesquisar Tese"): processar_ia("Me dê jurisprudência sobre...", None, chat_data); st.rerun()

    # --- CHAT ---
    for msg in chat_data["history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Botão de Word (Aparece só nas respostas da IA)
            if msg["role"] == "assistant":
                doc_file = gerar_word(msg["content"])
                if doc_file:
                    st.download_button(
                        label="📄 Baixar DOCX",
                        data=doc_file,
                        file_name=f"Carmelio_Analise_{int(time.time())}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"down_{hash(msg['content'])}"
                    )

    # --- INPUT (VOZ + TEXTO) ---
    st.divider()
    col_audio, col_text = st.columns([1, 5])
    
    with col_audio:
        audio_input = st.audio_input("Falar", key=f"aud_{st.session_state.current_chat_id}")
    
    with col_text:
        text_input = st.chat_input("Digite sua mensagem...")

    if audio_input or text_input:
        # Adiciona mensagem do usuário ao histórico visual
        user_msg = text_input if text_input else "🎤 (Mensagem de Voz enviada)"
        chat_data["history"].append({"role": "user", "content": user_msg})
        
        # Chama a IA
        processar_ia(text_input, audio_input, chat_data)
        st.rerun()

# --- EXECUÇÃO ---
if not st.session_state.logged_in:
    login()
else:
    sidebar_menu()
    main_app()
