import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
import mimetypes
from datetime import datetime
from docx import Document
from io import BytesIO

# --- 1. CONFIGURAÇÃO DE ALTO NÍVEL (UX/UI) ---
st.set_page_config(
    page_title="Carmélio AI - Legal Suite",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS AVANÇADO PARA IMITAR INTERFACE DE CHAT MODERNO
st.markdown("""
<style>
    /* Esconde elementos padrões do Streamlit que poluem a tela */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Estilo da Barra Lateral */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #dee2e6;
    }
    
    /* Estilo das Mensagens (Balões) */
    .stChatMessage {
        background-color: transparent;
        border: none;
    }
    .stChatMessage[data-testid="stChatMessageAvatarUser"] {
        background-color: #f0f2f6;
    }
    
    /* Área de Input Fixa no Rodapé (Tentativa de fixação visual) */
    .stChatInput {
        position: fixed;
        bottom: 0;
        z-index: 1000;
    }
    
    /* Botões de Ação Rápida (Sugestões) */
    .action-btn {
        border: 1px solid #e0e0e0;
        border-radius: 20px;
        padding: 5px 15px;
        margin: 5px;
        font-size: 0.8rem;
        background-color: white;
        color: #333;
        transition: 0.3s;
    }
    .action-btn:hover {
        background-color: #eef;
        border-color: #ccd;
    }

    /* Ajuste do Áudio Input para ficar discreto */
    .stAudioInput {
        margin-top: -20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. GERENCIAMENTO DE SESSÃO E ESTADO ---
# Inicialização robusta de todas as variáveis
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "chats" not in st.session_state:
    # Cria o primeiro chat padrão
    st.session_state.chats = {"chat_init": {"title": "Nova Conversa", "history": [], "file": None}}
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = "chat_init"
if "tom" not in st.session_state: st.session_state.tom = "Formal (Jurídico)"
if "processing" not in st.session_state: st.session_state.processing = False

# --- 3. MÓDULO DE SEGURANÇA E ARQUIVOS ---
def gerar_docx_seguro(texto_md):
    """Converte Markdown para DOCX de forma segura"""
    try:
        doc = Document()
        doc.add_heading('Relatório Carmélio AI', 0)
        doc.add_paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
        doc.add_paragraph('---')
        
        # Limpeza básica de Markdown para texto plano (melhoria futura: parser real)
        texto_limpo = texto_md.replace("**", "").replace("##", "").replace("###", "")
        
        for paragrafo in texto_limpo.split('\n'):
            if paragrafo.strip():
                doc.add_paragraph(paragrafo)
                
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Erro ao gerar DOCX: {e}")
        return None

def upload_handler(uploaded_file):
    """Gerencia upload com retries, validação de MIME e limpeza"""
    if not uploaded_file: return None
    
    try:
        # 1. Validação de Tipo
        mime_type = mimetypes.guess_type(uploaded_file.name)[0]
        if not mime_type: mime_type = 'application/octet-stream'
        
        # 2. Sanitização do Nome
        nome_limpo = "".join([c for c in uploaded_file.name if c.isalnum() or c in "._- "])
        
        # 3. Salvar Temporário
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
            
        # 4. Envio para Google com Timeout
        try:
            file_ref = genai.upload_file(path=tmp_path, mime_type=mime_type, display_name=nome_limpo)
            
            # Loop de espera (Polling)
            timeout = 60
            start = time.time()
            while file_ref.state.name == "PROCESSING":
                if time.time() - start > timeout:
                    raise TimeoutError("Timeout do Google")
                time.sleep(1)
                file_ref = genai.get_file(file_ref.name)
                
            if file_ref.state.name == "FAILED":
                raise ValueError("Google rejeitou o arquivo")
                
            return file_ref
            
        finally:
            # Limpeza do disco sempre acontece, mesmo com erro
            if os.path.exists(tmp_path): os.remove(tmp_path)
            
    except Exception as e:
        st.error(f"Erro crítico no upload: {e}")
        return None

# --- 4. MÓDULO DE AUTENTICAÇÃO ---
def tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>⚖️ Carmélio AI</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: grey;'>Sistema de Inteligência Jurídica v10.0</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        usuario = st.text_input("Usuário", placeholder="Seu usuário de acesso")
        senha = st.text_input("Senha", type="password", placeholder="Sua senha segura")
        
        if st.button("Entrar no Sistema", type="primary", use_container_width=True):
            creds = st.secrets.get("passwords", {})
            if usuario in creds and str(creds[usuario]) == str(senha):
                st.session_state.logged_in = True
                st.session_state.username = usuario
                st.rerun()
            else:
                st.error("🔒 Acesso Negado. Credenciais inválidas.")

# --- 5. NÚCLEO DE INTELIGÊNCIA (LLM) ---
def motor_ia(prompt_usuario, audio_input, chat_data):
    """O Cérebro da Operação"""
    
    # Previne execução dupla
    if st.session_state.processing: return
    st.session_state.processing = True
    
    try:
        # Configura API
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash") # Modelo mais estável
        
        historico_api = []
        
        # 1. Injeta Personalidade (System Prompt)
        personas = {
            "Formal (Jurídico)": "Você é um Advogado Sênior. Use linguagem técnica, cite leis (CF/88, CPC, CC) e seja formal.",
            "Didático (Cliente)": "Você é um consultor explicando para leigos. Use metáforas, evite 'juridiquês' e seja empático.",
            "Executivo (Resumo)": "Você é um analista focado em dados. Responda APENAS com bullet points, datas e valores."
        }
        sys_msg = f"Persona: {personas.get(st.session_state.tom, '')}. Responda sempre em Markdown."
        historico_api.append({"role": "user", "parts": [sys_msg]})
        historico_api.append({"role": "model", "parts": ["Compreendido. Seguirei a persona."]})
        
        # 2. Injeta Arquivo (Contexto)
        if chat_data["file"]:
            historico_api.append({"role": "user", "parts": [chat_data["file"], "Este é o documento de referência para nossa conversa."]})
            historico_api.append({"role": "model", "parts": ["Documento analisado e carregado na memória."]})
            
        # 3. Processa Áudio Novo (Se houver)
        texto_extra = ""
        if audio_input:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as t:
                t.write(audio_input.getvalue()); tp = t.name
            ref_audio = genai.upload_file(path=tp, mime_type="audio/wav")
            
            # Espera processar o áudio
            while ref_audio.state.name == "PROCESSING": time.sleep(0.5); ref_audio = genai.get_file(ref_audio.name)
            
            historico_api.append({"role": "user", "parts": [ref_audio, "Transcreva e considere este áudio na sua resposta."]})
            historico_api.append({"role": "model", "parts": ["Áudio ouvido."]})
            os.remove(tp)
            texto_extra = " (Resposta baseada em Áudio)"

        # 4. Recupera Histórico da Conversa
        for msg in chat_data["history"]:
            role = "model" if msg["role"] == "assistant" else "user"
            # Filtra apenas conteúdo de texto para evitar erro de tipo
            historico_api.append({"role": role, "parts": [str(msg["content"])]})
            
        # 5. Define Prompt Final
        final_prompt = prompt_usuario if prompt_usuario else "Prossiga com a análise do contexto enviado (arquivo ou áudio)."
        
        # 6. Chamada à API
        chat_session = model.start_chat(history=historico_api)
        resposta = chat_session.send_message(final_prompt)
        
        # 7. Salva Resultado
        chat_data["history"].append({"role": "assistant", "content": resposta.text + texto_extra})
        
        # 8. Renomeia Chat se for novo
        if chat_data["title"] == "Nova Conversa":
            try:
                titulo = model.generate_content(f"Crie um título de 3 palavras para: {final_prompt}").text.strip()
                chat_data["title"] = titulo
            except: pass

    except Exception as e:
        st.error(f"Erro na IA: {e}")
        chat_data["history"].append({"role": "assistant", "content": f"❌ Ocorreu um erro técnico: {str(e)}"})
    
    finally:
        st.session_state.processing = False
        st.rerun()

# --- 6. INTERFACE PRINCIPAL (BARRA LATERAL E CHAT) ---
def sidebar_sistema():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown("---")
        
        # Configuração de Tom
        st.markdown("**🧠 Personalidade da IA**")
        st.session_state.tom = st.selectbox(
            "Estilo de Resposta:",
            ["Formal (Jurídico)", "Didático (Cliente)", "Executivo (Resumo)"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("**🗂️ Gestão de Conversas**")
        
        if st.button("➕ Nova Conversa", type="primary", use_container_width=True):
            new_id = f"chat_{int(time.time())}"
            st.session_state.chats[new_id] = {"title": "Nova Conversa", "history": [], "file": None}
            st.session_state.current_chat_id = new_id
            st.rerun()
            
        # Lista de Chats (Scrollable)
        ids_chats = list(st.session_state.chats.keys())[::-1]
        for cid in ids_chats:
            cdata = st.session_state.chats[cid]
            # Formatação visual do botão
            label = cdata['title']
            if len(label) > 22: label = label[:20] + "..."
            if cid == st.session_state.current_chat_id: label = f"📂 {label}"
            
            if st.button(label, key=cid, use_container_width=True):
                st.session_state.current_chat_id = cid
                st.rerun()
                
        st.markdown("---")
        if st.button("🚪 Sair do Sistema"):
            st.session_state.logged_in = False
            st.rerun()

def chat_interface():
    # Recupera dados do chat ativo
    chat_id = st.session_state.current_chat_id
    chat_data = st.session_state.chats[chat_id]
    
    st.header(chat_data['title'])
    
    # --- ÁREA 1: CONTEXTO (ARQUIVO) ---
    with st.expander("📎 Contexto / Arquivos Anexados", expanded=not chat_data["file"]):
        if not chat_data["file"]:
            uploaded = st.file_uploader(
                "Arraste PDF, Áudio ou Imagem aqui", 
                type=["pdf", "jpg", "png", "mp3", "wav", "m4a"],
                key=f"upl_{chat_id}"
            )
            if uploaded:
                with st.spinner("Enviando para o servidor seguro..."):
                    ref = upload_handler(uploaded)
                    if ref:
                        chat_data["file"] = ref
                        chat_data["history"].append({"role": "assistant", "content": f"✅ Arquivo **{uploaded.name}** indexado com sucesso. O que deseja saber?"})
                        st.rerun()
        else:
            st.success(f"Arquivo ativo: **{chat_data['file'].display_name}**")
            if st.button("🗑️ Remover Arquivo", key=f"del_{chat_id}"):
                chat_data["file"] = None
                st.rerun()

    # --- ÁREA 2: FEED DE MENSAGENS ---
    # Container para mensagens (deixa espaço para o input fixo embaixo)
    chat_container = st.container()
    
    with chat_container:
        # Mostra sugestões se estiver vazio
        if not chat_data["history"] and chat_data["file"]:
            st.info("💡 Sugestões de início:")
            c1, c2, c3 = st.columns(3)
            if c1.button("📝 Resumir Documento"):
                chat_data["history"].append({"role": "user", "content": "Faça um resumo executivo."})
                motor_ia("Faça um resumo executivo.", None, chat_data)
            if c2.button("📅 Extrair Prazos"):
                chat_data["history"].append({"role": "user", "content": "Quais são as datas importantes?"})
                motor_ia("Liste todas as datas e prazos.", None, chat_data)
            if c3.button("⚖️ Analisar Riscos"):
                chat_data["history"].append({"role": "user", "content": "Quais os riscos jurídicos?"})
                motor_ia("Aponte cláusulas de risco.", None, chat_data)

        # Renderiza Mensagens
        for msg in chat_data["history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # Botão de Download inteligente (só aparece em respostas longas da IA)
                if msg["role"] == "assistant" and len(msg["content"]) > 100:
                    docx_file = gerar_docx_seguro(msg["content"])
                    if docx_file:
                        st.download_button(
                            label="⬇️ Baixar DOCX",
                            data=docx_file,
                            file_name="Carmelio_Analise.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"down_{hash(msg['content'])}"
                        )

        # Elemento vazio para dar margem ao fundo (scroll)
        st.markdown("<div style='height: 150px;'></div>", unsafe_allow_html=True)

    # --- ÁREA 3: INPUT FIXO (RODAPÉ) ---
    # Esta área fica "presa" no fundo da tela visualmente
    
    # Separador visual
    st.markdown("---") 
    
    col_mic, col_text = st.columns([1, 6])
    
    with col_mic:
        # Novo componente de áudio nativo
        audio_blob = st.audio_input("Falar", key=f"mic_{chat_id}")
    
    with col_text:
        prompt_text = st.chat_input("Digite sua mensagem para o Carmélio AI...", key=f"txt_{chat_id}")

    # GATILHO DE ENVIO UNIFICADO
    if prompt_text or audio_blob:
        # Se usuário falou ou digitou
        msg_user = prompt_text if prompt_text else "🎤 [Áudio Enviado]"
        
        # 1. Adiciona msg do user ao histórico
        chat_data["history"].append({"role": "user", "content": msg_user})
        
        # 2. Roda a IA (passando texto e áudio se houver)
        motor_ia(prompt_text, audio_blob, chat_data)

# --- 7. EXECUTOR PRINCIPAL ---
if __name__ == "__main__":
    if not st.session_state.logged_in:
        tela_login()
    else:
        sidebar_sistema()
        chat_interface()
