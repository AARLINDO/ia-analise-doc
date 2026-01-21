import streamlit as st
import time
from datetime import datetime, timedelta

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================
st.set_page_config(page_title="Carmélio AI | Suíte Jurídica Pro", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #12141C; border-right: 1px solid #2B2F3B; }
    .timer-display { font-size: 90px; font-weight: bold; color: #FFFFFF; text-align: center;
        text-shadow: 0 0 30px rgba(59, 130, 246, 0.6); margin: 20px 0; font-family: 'Courier New', monospace; }
    .timer-status { font-size: 22px; text-transform: uppercase; letter-spacing: 3px; color: #3B82F6;
        text-align: center; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# ESTADO
# =============================================================================
if "focus_sessions" not in st.session_state:
    st.session_state.focus_sessions = []

# =============================================================================
# MENU
# =============================================================================
menu = st.sidebar.radio("Menu Principal:", [
    "🎓 Área do Estudante", "💬 Mentor Jurídico", "📄 Contratos", "🏢 Cartório OCR",
    "🎙️ Transcrição", "🍅 Sala de Foco (Pomodoro)", "⭐ Feedback", "📊 Logs", "👤 Sobre"
])

# =============================================================================
# MÓDULO POMODORO
# =============================================================================
if menu == "🍅 Sala de Foco (Pomodoro)":
    st.title("🍅 Sala de Foco & Produtividade")

    # Seleção de ciclo
    modo_foco = st.radio("Selecione o ciclo:", [
        "Passos de bebê (10 min)", "Popular (20 min)", "Médio (40 min)", "Estendido (60 min)", "Personalizado"
    ], index=1)

    if modo_foco == "Personalizado":
        tempo_selecionado = st.slider("Minutos:", 5, 120, 25)
    else:
        tempo_selecionado = int(re.search(r'\d+', modo_foco).group())

    # Configurações extras
    col1, col2 = st.columns(2)
    with col1:
        som = st.selectbox("Alarme:", ["Ding", "Bip", "Mudo"])
    with col2:
        notificacao = st.toggle("Notificar ao terminar", value=True)

    st.markdown("---")

    # Timer visual
    col_timer = st.columns([1, 2, 1])[1]
    with col_timer:
        if st.button("▶️ Iniciar Sessão", use_container_width=True):
            status_text = st.empty()
            timer_text = st.empty()
            progresso = st.progress(0)

            total_segundos = tempo_selecionado * 60
            inicio = datetime.now()

            for i in range(total_segundos):
                restante = total_segundos - i
                mins, secs = divmod(restante, 60)
                time_str = f"{mins:02d}:{secs:02d}"

                timer_text.markdown(f"<div class='timer-display'>{time_str}</div>", unsafe_allow_html=True)
                status_text.markdown(f"<div class='timer-status'>FOCADO • {modo_foco}</div>", unsafe_allow_html=True)
                progresso.progress((i + 1) / total_segundos)

                time.sleep(1)

            # Fim do ciclo
            timer_text.markdown(f"<div class='timer-display'>00:00</div>", unsafe_allow_html=True)
            st.balloons()
            st.success(f"🎉 Ciclo de {tempo_selecionado} min concluído!")

            # Registrar sessão
            fim = datetime.now()
            st.session_state.focus_sessions.append({
                "modo": modo_foco,
                "inicio": inicio.strftime("%H:%M"),
                "fim": fim.strftime("%H:%M"),
                "duracao": tempo_selecionado
            })

            # Alarme sonoro
            if som != "Mudo":
                st.markdown("""
                    <audio autoplay>
                    <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3">
                    </audio>
                """, unsafe_allow_html=True)

            # Notificação
            if notificacao:
                st.toast("⏰ Seu ciclo de foco terminou!", icon="⌛")

    st.markdown("---")
    st.markdown("### 📊 Histórico de sessões")
    if st.session_state.focus_sessions:
        for s in st.session_state.focus_sessions[-10:]:
            st.write(f"- {s['modo']} | {s['inicio']} → {s['fim']} | {s['duracao']} min")
    else:
        st.info("Nenhuma sessão registrada ainda.")
