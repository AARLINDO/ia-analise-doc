import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# --- 1. CONFIGURAÇÃO VISUAL PREMIUM ---
st.set_page_config(
    page_title="Carmélio AI - Análise Jurídica",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PARA REMOVER MARCAS DO STREAMLIT (VISUAL LIMPO) ---
st.markdown("""
<style>
    /* Esconde o menu de 'Deploy' e o rodapé padrão */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    #stDecoration {display:none;}
    
    /* Estilo para o rodapé personalizado */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f0f2f6;
        color: #31333F;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #dcdcdc;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO COM O GOOGLE ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("⚠️ Erro de configuração: Chave de API não encontrada.")
    st.stop()

# --- 3. INSTRUÇÃO DO SISTEMA (PERSONA) ---
SYSTEM_PROMPT = """
Você é o assistente virtual da 'Carmélio Soluções Jurídicas'.
Seu tom deve ser: Profissional, Objetivo e Seguro.
Ao analisar documentos, foque em riscos legais, prazos e valores.
Sempre responda em Português Formal.
"""

# --- 4. GERENCIAMENTO DE MEMÓRIA ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "uploaded_file_ref" not in st.session_state:
    st.session_state.uploaded_file_ref = None

# --- 5. BARRA LATERAL (PERFIL PROFISSIONAL) ---
with st.sidebar:
    st.title("⚖️ Carmélio AI")
    st.markdown("**Inteligência Jurídica & Documental**")
    st.markdown("---")
    
    st.info("📂 **Upload de Documento**")
    uploaded_file = st.file_uploader("Arraste o PDF ou Imagem aqui:", type=["pdf", "png", "jpg", "jpeg"])

    if uploaded_file:
        st.success("✅ Arquivo carregado!")
        if st.button("🗑️ Nova Análise (Limpar)"):
            st.session_state.chat_history = []
            st.session_state.uploaded_file_ref = None
            st.rerun()
            
    st.markdown("---")
    st.markdown("### Sobre")
    st.markdown("""
    Ferramenta desenvolvida para agilizar a leitura de editais, 
    contratos e certidões.
    
    **Desenvolvedor:** Arthur Carmélio
    **Versão:** 2.1 Pro
    """)

# --- 6. TELA PRINCIPAL ---
st.header("📄 Análise Documental Inteligente")

# Aviso de isenção de responsabilidade (Essencial para parecer profissional)
st.caption("⚠️ Nota: Esta ferramenta utiliza IA para auxiliar na análise. Sempre confira os dados originais no documento.")

if uploaded_file:
    # Processamento do Arquivo
    if st.session_state.uploaded_file_ref is None:
        with st.status("🔍 Processando documento...", expanded=True) as status:
            st.write("Lendo arquivo...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            st.write("Enviando para análise segura...")
            upload_ref = genai.upload_file(tmp_path)
            
            # Aguarda o processamento do Google (importante para arquivos grandes)
            while upload_ref.state.name == "PROCESSING":
                time.sleep(2)
                upload_ref = genai.get_file(upload_ref.name)
            
            st.session_state.uploaded_file_ref = upload_ref
            
            # Mensagem inicial automática
            welcome_msg = "Olá. O documento foi processado com sucesso. Posso fazer um resumo executivo, extrair datas ou responder dúvidas específicas."
            st.session_state.chat_history.append({"role": "assistant", "content": welcome_msg})
            
            status.update(label="✅ Documento pronto para análise!", state="complete", expanded=False)
            os.remove(tmp_path)

    # Exibe o chat
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Campo de Entrada
    prompt = st.chat_input("Digite sua pergunta sobre o documento...")

    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                try:
                    # Usando o modelo que funcionou para você
                    model = genai.GenerativeModel(
                        "gemini-3-flash-preview", 
                        system_instruction=SYSTEM_PROMPT
                    )
                    
                    chat = model.start_chat(history=[
                        {"role": "user", "parts": [st.session_state.uploaded_file_ref, "Analise este arquivo."]},
                        {"role": "model", "parts": ["Arquivo recebido."]}
                    ])
                    
                    response = chat.send_message(prompt)
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    
                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")
                    st.warning("Dica: Se o erro persistir, tente limpar a conversa na barra lateral.")

else:
    # Tela de "Descanso" (Quando não tem arquivo)
    st.info("👈 Por favor, faça o upload de um documento na barra lateral para começar.")
    
# --- 7. RODAPÉ PERSONALIZADO ---
st.markdown("""
<div class="footer">
    Desenvolvido por <b>Arthur Carmélio</b> | © 2026 Todos os direitos reservados.
</div>
""", unsafe_allow_html=True)
