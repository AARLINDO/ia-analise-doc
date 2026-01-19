import streamlit as st
import google.generativeai as genai
import tempfile
import os

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="ChatDoc IA",
    page_icon="🤖",
    layout="wide"
)

# Estilo CSS para esconder menus chatos e deixar mais limpo
st.markdown("""
<style>
    .stDeployButton {display:none;}
    div[data-testid="stSidebar"] {background-color: #f0f2f6;}
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO COM O GOOGLE ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("⚠️ Configure a chave de API nos 'Secrets' do Streamlit.")
    st.stop()

# --- 3. MEMÓRIA DA SESSÃO ---
# Isso faz o site lembrar da conversa e do arquivo enquanto você usa
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "uploaded_file_ref" not in st.session_state:
    st.session_state.uploaded_file_ref = None

# --- 4. BARRA LATERAL (UPLOAD) ---
with st.sidebar:
    st.title("📂 Documento")
    st.info("Faça upload de um PDF para conversar com ele.")
    uploaded_file = st.file_uploader("Escolha o arquivo:", type=["pdf", "png", "jpg"])

    if uploaded_file:
        # Botão para limpar a conversa se trocar de assunto
        if st.button("🗑️ Limpar Conversa"):
            st.session_state.chat_history = []
            st.rerun()

# --- 5. LÓGICA PRINCIPAL ---
st.title("🤖 ChatDoc Pro")
st.caption("Converse com seus documentos usando Inteligência Artificial")

if uploaded_file:
    # --- Processamento do Arquivo (Só roda se mudar o arquivo) ---
    if st.session_state.uploaded_file_ref is None:
        with st.spinner("Processando documento..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            # Envia para o Google e guarda a referência na memória
            upload_ref = genai.upload_file(tmp_path)
            st.session_state.uploaded_file_ref = upload_ref
            
            # Adiciona mensagem inicial da IA
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": "Olá! Li seu documento. O que você gostaria de saber sobre ele?"
            })
            os.remove(tmp_path) # Limpa o arquivo do PC

    # --- Exibir o Histórico da Conversa ---
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- CAMPO DE DIGITAÇÃO (A Mágica Acontece Aqui) ---
    prompt = st.chat_input("Pergunte algo sobre o arquivo (ex: 'Resuma os prazos')...")

    if prompt:
        # 1. Mostra o que o usuário digitou
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # 2. IA Pensa e Responde
        with st.chat_message("assistant"):
            with st.spinner("Lendo e pensando..."):
                try:
                    # Configura o modelo (Usando o que funcionou pra você)
                    model = genai.GenerativeModel("gemini-3-flash-preview")
                    
                    # Monta o histórico para enviar pra IA
                    # (Envia o arquivo + as últimas perguntas para ela ter contexto)
                    chat = model.start_chat(history=[
                        {"role": "user", "parts": [st.session_state.uploaded_file_ref, "Analise este arquivo."]},
                        {"role": "model", "parts": ["Entendido. O arquivo foi analisado."]}
                    ])
                    
                    # Envia a pergunta atual
                    response = chat.send_message(prompt)
                    st.markdown(response.text)
                    
                    # Salva a resposta no histórico
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    
                except Exception as e:
                    st.error(f"Erro: {e}")

else:
    # Tela de boas-vindas (sem arquivo)
    st.markdown("### ⬅️ Comece fazendo upload de um PDF na barra lateral.")
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/PDF_file_icon.svg/833px-PDF_file_icon.svg.png", width=100)
