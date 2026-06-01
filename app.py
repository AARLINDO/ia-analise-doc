import streamlit as st
import streamlit.components.v1 as components
import os
import json
import time
import re
import random
from datetime import datetime, date
from io import BytesIO

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Ultimate Studio",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 2. IMPORTAÇÕES E SETUP
# =============================================================================
try: 
    import google.generativeai as genai
except ImportError: 
    genai = None

try: 
    import pdfplumber
except ImportError: 
    pdfplumber = None

try: 
    import docx
    from docx import Document
except ImportError: 
    docx = None
    Document = None

try: 
    from PIL import Image
except ImportError: 
    Image = None

# Inicialização de Estado (Session State)
keys = {
    "user_xp": 0, "contract_step": 1, "contract_clauses": [], 
    "contract_meta": {}, "chat_history": [], "edital_text": "", 
    "edital_filename": "", "quiz_data": None, "quiz_show_answer": False, 
    "user_choice": None, "ocr_text": "", "last_call": 0
}
for k, v in keys.items():
    if k not in st.session_state: 
        st.session_state[k] = v

# =============================================================================
# 3. FUNÇÕES UTILITÁRIAS E LÓGICA (BACKEND)
# =============================================================================

def check_rate_limit():
    """Evita chamadas excessivas (proteção simples)."""
    if time.time() - st.session_state.last_call < 2.0: 
        return True 
    return False

def mark_call(): 
    st.session_state.last_call = time.time()

def add_xp(amount):
    st.session_state.user_xp += amount
    st.toast(f"+{amount} XP | Nível {int(st.session_state.user_xp/100)}", icon="⚡")

@st.cache_resource
def get_best_model():
    """Configura e retorna o melhor modelo Gemini disponível (Modelos Top Atualizados)."""
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key: 
        return None, "⚠️ Configure secrets.toml"
    try:
        genai.configure(api_key=api_key)
        try: 
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except: 
            return None, "Erro de Chave API"
        
        pref = [
            'models/gemini-1.5-pro',         
            'models/gemini-1.5-flash',       
            'models/gemini-1.5-flash-latest',
            'models/gemini-pro'
        ]
        escolhido = next((m for m in pref if m in models), models[0] if models else None)
        
        if escolhido: 
            return genai.GenerativeModel(escolhido.replace("models/", "")), escolhido.replace("models/", "")
        return None, "Nenhum modelo compatível."
    except Exception as e: 
        return None, f"Erro Fatal: {str(e)}"

def call_gemini(system_prompt, user_prompt, json_mode=False, image=None, use_search=False):
    """Função central de comunicação com a IA."""
    if check_rate_limit(): 
        time.sleep(1)
    
    mark_call()
    model, name = get_best_model()
    if not model: 
        return f"Erro: {name}"
    
    try:
        tools_config = 'google_search_retrieval' if use_search else None
        
        if image:
            response = model.generate_content([system_prompt, image, user_prompt])
        else:
            full_prompt = f"SYSTEM ROLE: {system_prompt}\nUSER REQUEST: {user_prompt}"
            if json_mode: 
                full_prompt += "\nFORMAT: Return ONLY valid JSON. No Markdown."
            
            if tools_config:
                try:
                    response = model.generate_content(full_prompt, tools=tools_config)
                except:
                    response = model.generate_content(full_prompt)
            else:
                response = model.generate_content(full_prompt)
                
        return response.text
    except Exception as e: 
        if "429" in str(e):
            return "⚠️ Limite de velocidade atingido. Aguarde 30 segundos e tente novamente."
        return f"Erro IA: {str(e)}"

def extract_json_surgical(text):
    """Extrai JSON de texto bagunçado."""
    try:
        text = text.replace("```json", "").replace("```", "")
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match: 
            return json.loads(match.group(0))
    except: 
        pass
    return None

def read_pdf_safe(file_obj):
    """Lê PDF e retorna texto."""
    if not pdfplumber: 
        return None
    try:
        text = ""
        with pdfplumber.open(BytesIO(file_obj.getvalue())) as pdf:
            for i, p in enumerate(pdf.pages):
                if i >= 300: 
                    break 
                text += (p.extract_text() or "") + "\n"
        return text if text.strip() else None
    except: 
        pass
    return None

def create_generic_docx(content, title="Documento Carmélio AI"):
    if not docx: 
        return None
    doc = Document()
    doc.add_heading(title, 0)
    for line in content.split('\n'):
        if line.strip(): 
            doc.add_paragraph(line.strip())
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_contract_docx(clauses, meta):
    if not docx: 
        return None
    doc = Document()
    doc.add_heading(meta.get('tipo', 'CONTRATO').upper(), 0)
    doc.add_paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y')}")
    doc.add_heading("1. QUALIFICAÇÃO", level=1)
    doc.add_paragraph(meta.get('partes', ''))
    doc.add_heading("2. DO OBJETO", level=1)
    doc.add_paragraph(meta.get('objeto', ''))
    for clause in clauses:
        doc.add_heading(clause.get('titulo', 'Cláusula'), level=1)
        for line in clause.get('conteudo', '').split('\n'):
            if line.strip(): 
                doc.add_paragraph(line.strip())
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def get_daily_verse():
    """Retorna um versículo dinâmico e diferente baseado rigorosamente no dia do ano."""
    versiculos = [
        {"ref": "Josué 1:9", "txt": "Seja forte e corajoso! Não se apavore nem desanime, pois o Senhor, o seu Deus, estará com você por onde você andar."},
        {"ref": "Filipenses 4:13", "txt": "Tudo posso naquele que me fortalece."},
        {"ref": "Salmos 37:5", "txt": "Entregue o seu caminho ao Senhor; confie nele, e ele agirá."},
        {"ref": "Isaías 41:10", "txt": "Não tema, pois estou com você; não tenha medo, pois sou o seu Deus. Eu o fortalecerei e o ajudarei."},
        {"ref": "Jeremias 29:11", "txt": "Porque sou eu que conheço os planos que tenho para vocês', diz o Senhor, 'planos de fazê-los prosperar."},
        {"ref": "Provérbios 16:3", "txt": "Consagre ao Senhor tudo o que você faz, e os seus planos serão bem-sucedidos."},
        {"ref": "Salmos 121:1-2", "txt": "Levanto os meus olhos para os montes e pergunto: De onde me vem o socorro? O meu socorro vem do Senhor."},
        {"ref": "2 Timóteo 1:7", "txt": "Pois Deus não nos deu espírito de covardia, mas de poder, de amor e de equilíbrio."},
        {"ref": "Salmos 23:1", "txt": "O Senhor é o meu pastor; de nada terei falta."},
        {"ref": "Isaías 40:31", "txt": "Mas aqueles que esperam no Senhor renovam as suas forças. Voam bem alto como águias; correm e não ficam exaustos."},
        {"ref": "Mateus 6:33", "txt": "Busquem, pois, em primeiro lugar o Reino de Deus e a sua justiça, e todas essas coisas serão acrescentadas a vocês."},
        {"ref": "Salmos 46:1", "txt": "Deus é o nosso refúgio e a nossa fortaleza, auxílio sempre presente na adversidade."},
        {"ref": "Romanos 8:28", "txt": "Sabemos que Deus age em todas as coisas para o bem
