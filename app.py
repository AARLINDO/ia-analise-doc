import streamlit as st
import google.generativeai as genai
import tempfile
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="DocuAnalysis AI",
    page_icon="⚖️",
    layout="wide"
)

# --- 2. CARREGAR A CHAVE SECRETA ---
# O código busca a chave automaticamente nos segredos do Streamlit Cloud
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except FileNotFoundError:
    # Se rodar localmente sem configurar, avisa o erro
    st.error("Erro: Chave de API não encontrada. Configure os 'Secrets' no Streamlit Cloud.")
    st.stop()
except KeyError:
    st.error("Erro: A chave 'GOOGLE_API_KEY' não foi definida nos segredos.")
    st.stop()

# --- 3. O "CÉREBRO" DA IA (Instrução do Especialista) ---
SYSTEM_INSTRUCTION = """
Você é um Auditor Jurídico e Analista de Documentos Sênior.
Sua função é analisar arquivos PDF e imagens para extrair dados com precisão forense.

DIRETRIZES OBRIGATÓRIAS:
1. RESUMO ESTRUTURADO: Comece sempre com um resumo executivo em tópicos.
2. EXTRAÇÃO DE DADOS: Identifique nomes, datas, valores monetários e números de processos/contratos.
3. ALERTA DE RISCO: Se for um contrato, destaque cláusulas que pareçam abusivas ou prazos críticos.
4. FIDELIDADE: Não invente informações. Se o texto estiver ilegível, informe "Ilegível".
5. IDIOMA: Português do Brasil (Formal e Técnico).
"""

# --- 4. INTERFACE DO USUÁRIO ---
st.title("⚖️ DocuAnalysis Pro")
st.markdown("### Inteligência Artificial para Análise Documental")
st.markdown("---")

# Layout de duas colunas
col1, col2 = st.columns([1, 2])

with col1:
    st.info("📂 **Área de Upload**")
    uploaded_file = st.file_uploader("Arraste seu PDF ou Imagem aqui", type=["pdf", "jpg", "png", "jpeg"])
    
    # Opções rápidas
    task_option = st.radio(
        "O que você deseja fazer?",
        ["Resumir o documento", "Extrair Cláusulas/Prazos", "Análise de Riscos", "Pergunta Personalizada"]
    )

with col2:
    result_container = st.container()

# --- 5. PROCESSAMENTO ---
if uploaded_file is not None:
    # Salva o arquivo temporariamente para enviar ao Google
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    # Botão de ação
    if col1.button("🔍 Analisar Documento", type="primary"):
        with result_container:
            with st.spinner("A IA está lendo e analisando cada página..."):
                try:
                    # Prepara a pergunta final
                    if task_option == "Pergunta Personalizada":
                        user_q = st.text_input("Sua pergunta:", value="Qual o objeto deste contrato?")
                        final_prompt = user_q
                    else:
                        final_prompt = f"Execute a seguinte tarefa: {task_option}"

                    # Envia para a IA
                    myfile = genai.upload_file(tmp_path)
                    model = genai.GenerativeModel("gemini-pro", system_instruction=SYSTEM_INSTRUCTION)
                    
                    response = model.generate_content([myfile, final_prompt])
                    
                    # Exibe o resultado
                    st.success("Análise Concluída!")
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error(f"Ocorreu um erro na análise: {e}")
                finally:
                    # Limpeza
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)


