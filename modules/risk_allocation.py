# modules/risk_allocation.py

import streamlit as st

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
