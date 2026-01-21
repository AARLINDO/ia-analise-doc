import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Scanner de Modelos", page_icon="🕵️")

st.title("🕵️ Scanner de Modelos do Google")

# 1. PEGA A CHAVE
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    st.success("✅ Chave Encontrada e Configurada!")
except:
    st.error("❌ Erro: Chave não encontrada no Secrets.")
    st.stop()

# 2. PERGUNTA PRO GOOGLE O QUE TEM DISPONÍVEL
st.subheader("Quais modelos sua chave pode acessar?")
if st.button("🔍 Escanear Modelos Agora"):
    try:
        # Tenta listar os modelos disponíveis
        modelos = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelos.append(m.name)
        
        if modelos:
            st.success(f"🎉 Encontramos {len(modelos)} modelos disponíveis!")
            st.write("Copie um desses nomes para usarmos no código:")
            st.code("\n".join(modelos))
        else:
            st.warning("⚠️ A conexão funcionou, mas a lista de modelos veio vazia. Sua conta do Google pode ter restrições de região.")
            
    except Exception as e:
        st.error("🚨 Erro Crítico ao conectar com o Google:")
        st.code(str(e))
        st.info("Dica: Se o erro for 403, sua chave foi bloqueada. Se for 404, a biblioteca está desatualizada.")
