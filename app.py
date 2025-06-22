import streamlit as st
import random

st.set_page_config(page_title="Klickspiel", layout="centered")

st.markdown("<h1 style='text-align: center;'>🎯 Klick den Button!</h1>", unsafe_allow_html=True)

# Session State initialisieren
if "score" not in st.session_state:
    st.session_state.score = 0
if "chance" not in st.session_state:
    st.session_state.chance = 0
if "highscore" not in st.session_state:
    st.session_state.highscore = 0

# Button in der Mitte anzeigen
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 Klick mich!", use_container_width=True):
        st.session_state.score += 1
        st.session_state.chance += 1

        # Prüfe, ob zurückgesetzt wird
        if random.randint(1, 100) <= st.session_state.chance:
            st.warning("💥 Zurückgesetzt!")
            if st.session_state.score > st.session_state.highscore:
                st.session_state.highscore = st.session_state.score
            st.session_state.score = 0
            st.session_state.chance = 0

# Anzeige
st.metric(label="🔢 Aktueller Score", value=st.session_state.score)
st.metric(label="📈 Reset-Wahrscheinlichkeit", value=f"{st.session_state.chance}%")
st.metric(label="🏆 Highscore", value=st.session_state.highscore)
