import streamlit as st
import random

st.set_page_config(page_title="Klickspiel", layout="centered")

st.markdown("<h1 style='text-align: center;'>🎯 Klick den Button!</h1>", unsafe_allow_html=True)

# Session State initialisieren
if "score" not in st.session_state:
    st.session_state.score = 0
if "chance" not in st.ses

# Anzeige
st.metric(label="🔢 Aktueller Score", value=st.session_state.score)
st.metric(label="📈 Reset-Wahrscheinlichkeit", value=f"{st.session_state.chance}%")
st.metric(label="🏆 Highscore", value=st.session_state.highscore)

