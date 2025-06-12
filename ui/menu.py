# ui/menu.py

import streamlit as st

def display_sidebar():
    st.sidebar.title("📂 Navigation")
    return st.sidebar.radio(
        "Choose Option",
        ["-- Select an Action --", "Scan Market", "Risk Allocation", "Generate Profit Plan", "GPT Market Summary"]
    )
