# ui/menu.py

import streamlit as st

def display_sidebar():
    st.sidebar.title("📂 Navigation")

    # Optional AI feature toggle
    st.sidebar.markdown("### 🔧 Preferences")
    st.sidebar.checkbox("Enable AI Analysis", value=True, key="use_ai")

    return st.sidebar.radio(
        "Choose Option",
        ["-- Select an Action --", "Scan Market", "Risk Allocation", "Generate Profit Plan", "GPT Market Summary"]
    )
