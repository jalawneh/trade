# modules/risk_allocation.py

import streamlit as st
from utils.openai_helper import call_openai_chat, is_ai_enabled

def show_risk_allocation():
    st.title("⚖️ Set Risk Allocation")
    with st.form("allocation_form"):
        col1, col2, col3 = st.columns(3)
        low = col1.number_input("Low Risk %", 0, 100, st.session_state.low_risk)
        med = col2.number_input("Medium Risk %", 0, 100, st.session_state.med_risk)
        high = col3.number_input("High Risk %", 0, 100, st.session_state.high_risk)
        submitted = st.form_submit_button("Save Allocation")
    if submitted:
        if low + med + high != 100:
            st.error("❌ The total must equal 100%.")
        else:
            st.session_state.low_risk = low
            st.session_state.med_risk = med
            st.session_state.high_risk = high
            st.success("✅ Allocations saved.")

    if is_ai_enabled():
        st.markdown("---")
        st.markdown("### 🤖 AI Suggestion")
        prompt = """
        You are a risk management advisor for day traders. Suggest an ideal low, medium, and high risk allocation percentage for a user with a $3000 budget targeting $100 daily profit, assuming conservative to moderate trading style.
        """
        suggestion = call_openai_chat(prompt)
        if suggestion:
            st.info(suggestion)
        else:
            st.warning("AI response not available. Check your API configuration.")

        st.markdown("### 🗭 Sentiment Summary")
        sentiment_prompt = """
        Provide a brief sentiment analysis of current market risk appetite relevant to day traders based on typical trading news and volatility signals.
        Summarize with a score (0–10) and a trend label (e.g., Bullish, Bearish, Neutral).
        """
        sentiment_response = call_openai_chat(sentiment_prompt)
        if sentiment_response:
            st.success(sentiment_response)
        else:
            st.info("Sentiment summary not available.")
