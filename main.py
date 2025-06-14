# --- main.py ---
import streamlit as st
# ✅ MUST be the first Streamlit command
# --- Config and Title ---
st.set_page_config(page_title="Day Trading Scanner", layout="wide")

from utils.init_state import init_allocation_state
from ui.menu import display_sidebar
from modules.risk_allocation import show_risk_allocation
from modules.profit_plan import show_profit_plan
from modules.gpt_summary import show_gpt_summary
from modules.scan_market import scan_market


st.markdown("<h1 style='text-align: center; font-size: 60px;'>\U0001F4C8 Day Trader AI Agent</h1>", unsafe_allow_html=True)

# --- Session Init ---
init_allocation_state()

# --- Sidebar Menu ---
choice = display_sidebar()


# --- Action Routing ---
if choice == "Scan Market":
    scan_market()
elif choice == "Risk Allocation":
    show_risk_allocation()
elif choice == "Generate Profit Plan":
    show_profit_plan()
elif choice == "GPT Market Summary":
    show_gpt_summary()
