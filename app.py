import streamlit as st
import os
import json
import base64
import time
import re
from datetime import datetime
from io import BytesIO

# =============================================================================
# 1. ARQUITETURA E CONFIGURAÇÃO
# =============================================================================
st.set_page_config(
    page_title="Carmélio AI | Architect Edition",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PREMIUM & QUANTUM UI ---
st.markdown("""
<style>
    /* Base */
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #11141d; border-right: 1px solid #2B2F3B; }
    
    /* Tipografia e Títulos */
    h1, h2, h3 { font-family: 'Inter', sans-serif; letter-spacing: -0.5px; }
    .gradient-text {
        background: -webkit-linear-gradient(45deg, #3B82F6, #8B5CF6, #EC4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    
    /* Cards de Interface */
    .feature-card {
        background-color: #1F2430; border: 1px solid #374151;
        border-radius: 12px; padding: 20px; transition: transform 0.2s;
    }
    .feature-card:hover { border-color: #60A5FA; transform: translateY(-2px); }
    
    /* Inputs Profissionais */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #161B26 !important; 
        color: #F3F4F6 !important;
        border: 1px solid #374151 !important;
        border-radius: 8px;
    }
    
    /* Botões de Ação */
    div.stButton > button {
        background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 100%);
        color: white; border: none; font-weight: 600; padding: 0.5rem 1rem;
        border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    div.stButton > button:hover { opacity: 0.9; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2); }
    
    /* Gamificação Discreta */
    .xp-badge {
        background-color: #064E3B; color: #6EE7B7; 
        padding: 4px 12px; border-radius: 999px; 
        font-size: 12px; font-weight: bold; border: 1px solid #059669;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. SISTEMA DE DEPENDÊNCIAS RESILIENTE
# =============================================================================
# Carregamento com tratamento de erro silencioso mas funcional
@st.cache_resource
def load_libs():
    libs = {}
    try: from groq import Groq; libs['groq'] = Groq
    except ImportError: libs['groq'] = None
    
    try: import pdfplumber; libs['pdf'] = pdfplumber
    except ImportError: libs['pdf'] = None
    
    try: import docx; libs['docx'] = docx
    except ImportError: libs['docx'] = None
    
    try: from PIL import Image; libs['pil'] = Image
    except ImportError: libs['pil'] = None
    
    return libs

LIBS = load_libs()

# =============================================================================
# 3. ENGINE DE IA & UTILITÁRIOS AVANÇADOS
# =============================================================================

def get_ai_client():
    """Recupera o cliente Groq com tratamento de erro robusto."""
    api_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not api_key: return None
    if not LIBS['groq']: return None
    return LIBS['groq'](api_key=api_key)

def extract_json_surgical(text):
    """Extrai JSON mesmo que a IA 'converse' junto."""
    # Tenta achar o maior bloco JSON possível (array ou objeto)
    pattern = r"(\{[\s\S]*\}|\[[\s\S]*\])"
    match = re.search(pattern, text)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Tenta limpar vírgulas traidoras no final de listas (erro comum de LLM)
            json_str = re.sub(r",\s*([\]}])", r"\1", json_str)
            try: return json.loads(json_str)
            except: pass
    return None

def markdown_to_docx(doc_obj, text):
    """Converte Markdown básico (Negrito, Títulos) para formatação Word real."""
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        
        # Títulos
        if line.startswith('# '): doc_obj.add_heading(line[2:], 0)
        elif line.startswith('## '): doc_obj.add_heading(line[3:], 1)
        elif line.startswith('### '): doc_obj.add_heading(line[4:], 2)
        else:
            # Parágrafos com negrito
            p = doc_obj.add_paragraph()
            # Regex para **negrito**
            parts = re.split(r'(\*\*.*?\*\*)', line)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    run = p.add_run(part[2:-2])
                    run.bold = True
                else:
                    p.add_run(part)

def create_smart_docx(clauses_list, meta):
    if not LIBS['docx']: return None
    doc = LIBS['docx'].Document()
    
    # Cabeçalho Profissional
    doc.add_heading(meta.get('tipo', 'CONTRATO').upper(), 0)
    p = doc.add_paragraph()
    p.add_run(f"Data de Geração: {datetime.now().strftime('%d/%m/%Y')}").italic = True
    
    doc.add_heading('1. QUALIFICAÇÃO DAS PARTES', level=1)
    doc.add_paragraph(meta.get('partes', ''))
    
    doc.add_heading('2. DO OBJETO', level=1)
    doc.add_paragraph(meta.get('objeto', ''))
    
    # Cláusulas Dinâmicas
    for clause in clauses_list:
        doc.add_heading(clause.get('titulo', '').upper(), level=1)
        markdown_to_docx(doc, clause.get('conteudo', ''))
        
    return doc

def call_ai(system_prompt, user_prompt, temp=0.3, json_mode=False):
    """Função de chamada única e otimizada."""
    client = get_ai_client()
    if not client: return None
    
    try:
        kwargs = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "model": "llama-3.3-70b-versatile",
            "temperature": temp
        }
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Erro de Conexão Neural: {e}")
        return None

# =============================================================================
# 4. GAMIFICAÇÃO & ESTADO
# =============================================================================
if "user_xp" not in st.session_state: st.session_state.user_xp = 120
if "contract_step" not in st.session_state: st.session_state.contract_step = 1
if "contract_clauses" not in st.session_state: st.session_state.contract_clauses = []
if "chat_history" not in st.session_state: st.session_state.chat_history = []

def add_xp(amount, msg):
    st.session_state.user_xp += amount
    st.toast(f"+{amount} XP: {msg}", icon="⚡")

# =============================================================================
# 5. SIDEBAR INTELIGENTE
# =============================================================================
with st.sidebar:
    if os.path.exists("logo.jpg.png"):
        safe_image_show("logo.jpg.png")
    else:
        st.markdown("## ⚖️ Carmélio AI")
    
    st.markdown("---")
    
    # Navegação com Ícones
    menu = st.radio("Navegação:", [
        "🧠 Chat & Mentoria", 
        "📝 Redação Pro (Builder)", 
        "🎯 Mestre dos Editais", 
        "🏢 Cartório OCR", 
        "🎙️ Transcrição"
    ], label_visibility="collapsed")
    
    st.markdown("---")
    
    # Área do Usuário (Gamification Minimalista)
    lvl = int(st.session_state.user_xp / 100)
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; background:#1F2430; padding:10px; border-radius:8px;">
        <div>
            <span style="font-size:12px; color:#9CA3AF;">Nível {lvl}</span><br>
            <span style="font-weight:bold; color:white;">Advogado Jr.</span>
        </div>
        <div class="xp-badge">{st.session_state.user_xp} XP</div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(min((st.session_state.user_xp % 100) / 100, 1.0))
    
    st.markdown("---")
    c_li, c_wa = st.columns(2)
    c_li.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://linkedin.com)")
    c_wa.markdown("[![WhatsApp](https://img.shields.io/badge/WhatsApp-Chat-green)](https://wa.me/)")

# =============================================================================
# 6. MÓDULOS DE ALTA PERFORMANCE
# =============================================================================

# --- MÓDULO 1: CHAT MENTOR (CÉREBRO) ---
if menu == "🧠 Chat & Mentoria":
    st.markdown('<h1 class="gradient-text">Mentor Jurídico</h1>', unsafe_allow_html=True)
    
    if not st.session_state.chat_history:
        st.info("Olá, Doutor(a). Sou especialista em Direito Brasileiro e Tecnologia. Como posso auxiliar seus estudos ou casos hoje?")
        c1, c2 = st.columns(2)
        if c1.button("📚 Explicar Conceito Complexo"):
            st.session_state.chat_history.append({"role":"user", "content": "Explique a diferença entre Prescrição Intercorrente e Decadência no Processo Civil."})
            st.rerun()
        if c2.button("🔬 Análise de Tese (Quantum)"):
            st.session_state.chat_history.append({"role":"user", "content": "Analise possibilidades de teses de defesa para crime digital sob a ótica da Lei Carolina Dieckmann."})
            st.rerun()

    # Renderiza Chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Digite sua consulta..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Consultando jurisprudência e doutrina..."):
                # System Prompt Poderoso
                sys = """Você é o Carmélio AI, um jurista sênior e cientista da computação. 
                Responda com base na Legislação Brasileira (CF/88, CC, CPC, CP). 
                Seja didático para estudantes, mas técnico para advogados. 
                Use Markdown para formatar Artigos e Leis."""
                
                # Contexto curto para economizar tokens
                ctx = st.session_state.chat_history[-6:]
                
                # Concatena para envio
                full_ctx_str = "\n".join([f"{m['role']}: {m['content']}" for m in ctx])
                
                res = call_ai(sys, full_ctx_str, temp=0.4)
                
                if res:
                    st.write(res)
                    st.session_state.chat_history.append({"role": "assistant", "content": res})
                    add_xp(10, "Consulta Realizada")
                else:
                    st.error("Erro na conexão neural. Verifique sua chave API.")

# --- MÓDULO 2: REDAÇÃO JURÍDICA (BUILDER PRO) ---
elif menu == "📝 Redação Pro (Builder)":
    
    # Navegação Visual por Etapas
    st.markdown('<h2 class="gradient-text">Construtor de Peças & Contratos</h2>', unsafe_allow_html=True)
    step = st.session_state.contract_step
    
    # Progress Bar Inteligente
    cols = st.columns([1,1,1])
    cols[0].markdown(f"**1. Dados** {'✅' if step > 1 else '🟦'}")
    cols[1].markdown(f"**2. Estrutura** {'✅' if step > 2 else ('🟦' if step==2 else '⬜')}")
    cols[2].markdown(f"**3. Revisão** {'✅' if step > 3 else ('🟦' if step==3 else '⬜')}")
    st.progress(int(step/3 * 100))

    # ETAPA 1: BRIEFING
    if step == 1:
        with st.container():
            st.markdown("### 📝 Detalhes do Caso")
            tipo = st.text_input("Tipo de Documento", placeholder="Ex: Contrato de Prestação de Serviços de TI")
            
            c1, c2 = st.columns(2)
            partes = c1.text_area("Partes (Qualificação)", height=150, placeholder="Contratante: Nome, CPF...\nContratada: Nome, CNPJ...")
            objeto = c2.text_area("Objeto & Condições", height=150, placeholder="Descrição do serviço, valor, prazo, forma de pagamento...")
            
            if st.button("Gerar Estrutura Inteligente ➔", use_container_width=True):
                if tipo and objeto:
                    with st.spinner("🤖 A IA está desenhando a arquitetura jurídica do documento..."):
                        # Prompt Engenharia Jurídica
                        prompt = f"""
                        Atue como Advogado Sênior. Crie a estrutura de um(a) {tipo}.
                        Partes: {partes}
                        Objeto: {objeto}
                        
                        Gere um JSON com uma lista de cláusulas essenciais.
                        Inclua obrigatoriamente: Objeto, Obrigações, Pagamento, Prazo, Rescisão, LGPD, Foro.
                        Formato JSON: {{ "clauses": [ {{"titulo": "Nome da Cláusula", "conteudo": "Texto completo da cláusula..."}} ] }}
                        """
                        res_json = call_ai("Você é uma API que retorna apenas JSON.", prompt, json_mode=True)
                        data = extract_json_surgical(res_json)
                        
                        if data and 'clauses' in data:
                            st.session_state.contract_meta = {"tipo": tipo, "partes": partes, "objeto": objeto}
                            st.session_state.contract_clauses = data['clauses']
                            st.session_state.contract_step = 2
                            add_xp(20, "Estrutura Gerada")
                            st.rerun()
                        else:
                            st.error("Falha na estruturação. Tente simplificar os detalhes.")
                else:
                    st.warning("Preencha o Tipo e o Objeto para prosseguir.")

    # ETAPA 2: EDITOR DE CLÁUSULAS (O DIFERENCIAL)
    elif step == 2:
        st.markdown("### 📑 Editor Modular")
        st.info("Ajuste, remova ou adicione cláusulas antes de gerar o arquivo final.")
        
        # Botão Adicionar
        if st.button("➕ Adicionar Nova Cláusula Manual"):
            st.session_state.contract_clauses.append({"titulo": "Nova Cláusula", "conteudo": "Digite o texto..."})
            st.rerun()

        # Loop de Cláusulas (Cards Editáveis)
        to_remove = []
        for i, clause in enumerate(st.session_state.contract_clauses):
            with st.expander(f"{i+1}. {clause.get('titulo')}", expanded=False):
                new_title = st.text_input("Título", clause.get('titulo'), key=f"t_{i}")
                new_content = st.text_area("Conteúdo", clause.get('conteudo'), height=200, key=f"c_{i}")
                
                # Atualiza estado em tempo real
                st.session_state.contract_clauses[i] = {"titulo": new_title, "conteudo": new_content}
                
                if st.button("🗑️ Excluir Cláusula", key=f"del_{i}"):
                    to_remove.append(i)
        
        # Processa remoção
        if to_remove:
            for i in sorted(to_remove, reverse=True): del st.session_state.contract_clauses[i]
            st.rerun()

        # Navegação
        c_back, c_next = st.columns([1, 2])
        if c_back.button("⬅️ Voltar"):
            st.session_state.contract_step = 1
            st.rerun()
        if c_next.button("Finalizar e Revisar ➔", type="primary", use_container_width=True):
            st.session_state.contract_step = 3
            add_xp(30, "Documento Finalizado")
            st.rerun()

    # ETAPA 3: ENTREGA (VISUALIZAÇÃO + DOWNLOAD)
    elif step == 3:
        st.markdown("### ✅ Documento Pronto")
        
        c_view, c_chat = st.columns([2, 1])
        
        with c_view:
            # Monta texto visual
            full_text = f"# {st.session_state.contract_meta.get('tipo', 'DOCUMENTO')}\n\n"
            full_text += f"**PARTES:**\n{st.session_state.contract_meta.get('partes')}\n\n"
            for c in st.session_state.contract_clauses:
                full_text += f"## {c['titulo']}\n{c['conteudo']}\n\n"
            
            st.text_area("Visualização (Markdown)", full_text, height=600)
            
            # Geração do DOCX Real
            if LIBS['docx']:
                buffer = BytesIO()
                doc = LIBS['docx'].Document()
                create_smart_docx(st.session_state.contract_clauses, st.session_state.contract_meta)
                doc.save(buffer)
                buffer.seek(0)
                
                st.download_button(
                    label="💾 BAIXAR DOCX FORMATADO",
                    data=buffer,
                    file_name=f"{st.session_state.contract_meta.get('tipo', 'documento')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    use_container_width=True
                )
            else:
                st.warning("Biblioteca python-docx não detectada. Download desabilitado.")
                
            if st.button("✏️ Voltar e Editar"):
                st.session_state.contract_step = 2
                st.rerun()

        # Chat Lateral para Ajustes Finos
        with c_chat:
            with st.container(border=True):
                st.markdown("#### 🤖 Assistente de Revisão")
                st.caption("Peça para a IA reescrever cláusulas ou analisar riscos.")
                
                q = st.text_input("Ex: 'A multa da cláusula 3 está abusiva?'")
                if q:
                    with st.spinner("Analisando..."):
                        # Manda o contrato inteiro como contexto
                        ctx = f"Contrato Atual:\n{full_text}\n\nPergunta do usuário: {q}"
                        ans = call_ai("Você é um revisor de contratos.", ctx)
                        st.info(ans)

# --- MÓDULO 3: MESTRE DOS EDITAIS ---
elif menu == "🎯 Mestre dos Editais":
    st.title("🎯 Mestre dos Editais")
    st.info("Analise editais e gere planos de estudo focados.")
    
    file = st.file_uploader("Upload do Edital (PDF)", type=["pdf"])
    if file:
        st.success("Edital carregado! (Simulação de leitura ativa)")
        if st.button("Gerar Plano de Estudos"):
            with st.spinner("Criando estratégia..."):
                time.sleep(2)
                st.markdown("""
                ### 📅 Plano Sugerido
                * **Semana 1:** Direito Constitucional (Art. 5º) e Português (Crase).
                * **Semana 2:** Administrativo (Atos) e RLM.
                """)
                add_xp(15, "Plano Gerado")

# --- MÓDULO 4: OCR ---
elif menu == "🏢 Cartório OCR":
    st.title("🏢 Leitor de Documentos (OCR)")
    st.caption("Extração de texto de imagens e PDFs digitalizados.")
    
    u = st.file_uploader("Arquivo", type=["jpg", "png", "pdf"])
    if u and st.button("Extrair Texto"):
        with st.spinner("Processando via Visão Computacional..."):
            # Aqui entraria a chamada vision real se disponível
            prompt = "Transcreva este documento mantendo a formatação."
            if u.type in ['image/jpeg', 'image/png']:
                res = call_ai(prompt, u.getvalue(), type="vision") # Pseudo-code para futura implementação real
                # Fallback textual para o exemplo
                st.text_area("Texto Extraído (Simulação)", "CERTIDÃO DE INTEIRO TEOR...\n[Texto extraído apareceria aqui]", height=300)
            else:
                st.warning("OCR de PDF requer processamento extra. Use imagens para melhor resultado com Llama Vision.")

# --- MÓDULO 5: TRANSCRIÇÃO ---
elif menu == "🎙️ Transcrição":
    st.title("🎙️ Transcrição de Áudio")
    
    tab1, tab2 = st.tabs(["📂 Upload de Arquivo", "🎤 Gravação Ao Vivo"])
    
    with tab1:
        st.info("Para atas, reuniões e aulas gravadas.")
        f = st.file_uploader("Arquivo de Áudio", type=["mp3", "wav", "m4a"])
        if f and st.button("Transcrever Arquivo"):
            with st.spinner("Ouvindo e transcrevendo..."):
                res = call_ai("Transcreva", f.getvalue(), type="audio")
                st.success("Concluído!")
                st.text_area("Transcrição:", res, height=300)
                add_xp(20, "Áudio Transcrito")

    with tab2:
        st.info("Para ditados rápidos.")
        if hasattr(st, "audio_input"):
            mic = st.audio_input("Gravar")
            if mic:
                with st.spinner("Transcrevendo..."):
                    res = call_ai("Transcreva", mic.getvalue(), type="audio")
                    st.write(res)
        else:
            st.warning("Seu navegador não suporta gravação direta. Use o Upload.")
