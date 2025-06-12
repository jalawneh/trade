# modules/scan_market.py

import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import concurrent.futures
from io import StringIO
from modules.scan_utils import fetch_movers, analyze_stock

def scan_market():
    st.markdown("## 🔍 Market Scan Results")

    price_range = st.sidebar.slider("Price Range ($)", 1.0, 50.0, (5.0, 10.0), step=0.5, key="price_range")
    min_volume = st.sidebar.slider("Minimum Volume", 100_000, 5_000_000, 500_000, step=100_000, key="min_volume")
    min_volatility = st.sidebar.slider("Minimum Volatility (%)", 0.5, 10.0, 2.0, step=0.1, key="min_volatility")

    st.sidebar.markdown(f"""
    **Current Settings**
    - Price: ${price_range[0]:.2f} to ${price_range[1]:.2f}  
    - Volume ≥ {min_volume:,}  
    - Volatility ≥ {min_volatility:.1f}%
    """)

    tickers = fetch_movers()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(analyze_stock, tickers))

    results = [r for r in results if r and
               price_range[0] <= r["Last Close ($)"] <= price_range[1] and
               r["Volume"] >= min_volume and
               r["Volatility (%)"] >= min_volatility]

    if len(results) < 20:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            relaxed = list(executor.map(analyze_stock, tickers))
        results = [r for r in relaxed if r and
                   price_range[0] <= r["Last Close ($)"] <= price_range[1] and
                   r["Volume"] >= (min_volume * 0.6) and
                   r["Volatility (%)"] >= (min_volatility * 0.8)]

    if not results:
        st.warning("⚠️ No stocks matched your criteria.")
        return

    df = pd.DataFrame(results)
    df['Score'] = (
        df["Change (%)"].abs() * 0.4 +
        df["Volatility (%)"] * 0.4 +
        (df["Volume"] / 1_000_000) * 0.2
    )

    df['AI Recommendation (0–10)'] = 0
    df['AI Notes'] = ""

    ai_results = [("", 0)] * len(df)  # Skipping OpenAI call
    for i, (text, score) in enumerate(ai_results):
        df.at[i, 'AI Notes'] = text
        df.at[i, 'AI Recommendation (0–10)'] = score

    top30 = df.sort_values(by="Score", ascending=False).head(30)
    st.session_state['top10'] = top30
    st.success("✅ Top 30 Stocks Identified")

    st.dataframe(top30, use_container_width=True)

    buffer = StringIO()
    top30.to_string(buf=buffer, index=False)
    st.download_button("📥 Download Top 30", buffer.getvalue(), file_name="top30_stock_analysis.txt", mime="text/plain")

    for i, row in top30.reset_index().iterrows():
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(f"{i+1}. {row['Ticker']} - {row['Company Name']}")
            st.markdown(f"**Sector**: {row['Sector']}  \n**Volume**: {row['Volume']:,}  \n**Change**: {row['Change (%)']}%  \n**Volatility**: {row['Volatility (%)']}%  \n**AI Score**: {row['AI Recommendation (0–10)']}")
            with st.expander("📘 AI Notes"):
                st.markdown(row["AI Notes"])
        with col2:
            hist = yf.Ticker(row['Ticker']).history(period="7d", interval="1h")
            fig, ax = plt.subplots(figsize=(2, 1))
            ax.plot(hist.index, hist['Close'], linewidth=1)
            ax.set_title(f"{row['Ticker']}", fontsize=6)
            ax.tick_params(labelsize=5)
            ax.grid(True, linestyle="--", linewidth=0.5)
            st.pyplot(fig)
