# utils/init_state.py

import streamlit as st

def init_allocation_state():
    st.session_state.setdefault('low_risk', 60)
    st.session_state.setdefault('med_risk', 30)
    st.session_state.setdefault('high_risk', 10)
    st.session_state.setdefault('ai_enabled', True)  # Toggle for AI-based analysis