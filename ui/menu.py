# ui/menu.py

import streamlit as st

def display_sidebar():
    st.sidebar.title("📂 Navigation")

    # Preferences section
    st.sidebar.markdown("### 🔧 Preferences")
    st.sidebar.checkbox("Enable AI Analysis", value=True, key="use_ai")

    # ✅ GPT Model Selector
    AVAILABLE_MODELS = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]
    DEFAULT_MODEL = "gpt-3.5-turbo"
    st.sidebar.selectbox(
        "🤖 Select GPT Model",
        AVAILABLE_MODELS,
        index=AVAILABLE_MODELS.index(st.session_state.get("gpt_model", DEFAULT_MODEL)),
        key="gpt_model"
    )

    return st.sidebar.radio(
        "Choose Option",
        ["-- Select an Action --", "Scan Market", "Risk Allocation", "Generate Profit Plan", "GPT Market Summary"]
    )
