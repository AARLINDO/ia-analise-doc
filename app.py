import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="Diagnóstico Carmélio", page_icon="🔧", layout="wide")

st.title("🔧 Modo de Diagnóstico")

# 1. TESTE DO COFRE
st.subheader("1. Teste de Leitura da Chave")
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    # Mostra só o começo e o fim para conferir (segurança)
    mascara = f"{api_key[:6]}...{api_key[-4:]}"
    st.success(f"✅ Chave encontrada no cofre: {mascara}")
    
    # Configura o Google
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"❌ Erro ao ler Secrets: {e}")
    st.stop()

# 2. TESTE DE CONEXÃO COM O GOOGLE
st.subheader("2. Teste de Conexão Real")

if st.button("Testar Conexão com Google Agora"):
    with st.spinner("Chamando o Gemini..."):
        try:
            # Tenta o modelo mais simples primeiro
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content("Responda apenas: Sistema Operacional OK.")
            
            st.success("🎉 SUCESSO! O Google respondeu:")
            st.info(response.text)
            
        except Exception as e:
            st.error("🚨 O GOOGLE RECUSOU A CONEXÃO.")
            st.warning("Aqui está o erro exato (mande print disso):")
            st.code(str(e)) # AQUI VAI APARECER O MOTIVO REAL
