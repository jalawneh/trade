# modules/scan_market.py

import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import concurrent.futures
from io import StringIO
import plotly.graph_objects as go
from modules.scan_utils import fetch_movers, analyze_stock
from utils.openai_helper import analyze_stock_summary_and_details
import os

AVAILABLE_MODELS = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]
DEFAULT_MODEL = "gpt-3.5-turbo"


USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"
AI_STOCK_LIMIT = 15  # ✅ Limit AI calls to top N stocks

def run_ai_batch(df):
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        return list(executor.map(analyze_stock_summary_and_details, [row for _, row in df.iterrows()]))

def scan_market():
    st.markdown("## 🔍 Market Scan Results")

    model_used = st.session_state.get("gpt_model", "gpt-3.5-turbo")
    st.caption(f"🤖 Model in use: `{model_used}`")
    
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
    df['AI Notes'] = "⚠️ Not analyzed"
    df['AI Summary'] = "⚠️ Not analyzed"
    df['AI Score Label'] = ""

    if USE_OPENAI and st.session_state.get("use_ai", True):
        top_ai_df = df.sort_values(by="Score", ascending=False).head(AI_STOCK_LIMIT)
        ai_results = run_ai_batch(top_ai_df)

        for i, (idx, result) in enumerate(zip(top_ai_df.index, ai_results)):
            score = result["score"]
            df.at[idx, 'AI Summary'] = result["summary"]
            df.at[idx, 'AI Notes'] = result["ai_notes"]
            df.at[idx, 'AI Recommendation (0–10)'] = score
            df.at[idx, 'AI Score Label'] = result.get("score_label", "")

    top30 = df.sort_values(by="Score", ascending=False).head(30)
    st.session_state['top10'] = top30
    st.success("✅ Top 30 Stocks Identified")

    st.dataframe(
        top30[[
            'Ticker', 'Company Name', 'Previous Close ($)', 'Last Close ($)', 'Change (%)',
            'Volume', 'Volatility (%)', 'Sector', 'Score',
            'AI Recommendation (0–10)', 'AI Summary'
        ]],
        use_container_width=True
    )

    buffer = StringIO()
    top30[[
        'Ticker', 'Company Name', 'Previous Close ($)', 'Last Close ($)', 'Change (%)',
        'Volume', 'Volatility (%)', 'Sector', 'Score',
        'AI Recommendation (0–10)', 'AI Score Label', 'AI Summary', 'AI Notes'
    ]].to_string(buf=buffer, index=False)
    st.download_button("📥 Download Top 30", buffer.getvalue(), file_name="top30_stock_analysis.txt", mime="text/plain")

    for i, row in top30.reset_index().iterrows():
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(f"{i+1}. {row['Ticker']} - {row['Company Name']}")
            st.markdown(f"**Sector**: {row['Sector']}  \n**Volume**: {row['Volume']:,}  \n**Change**: {row['Change (%)']}%  \n**Volatility**: {row['Volatility (%)']}%  \n**AI Score**: {row['AI Recommendation (0–10)']}")
            with st.expander("📘 AI Notes"):
                st.markdown(row["AI Notes"])
        with col2:
            try:
                hist = yf.Ticker(row['Ticker']).history(period="90d", interval="1d")  # 📅 90-day daily data

                if hist.empty or len(hist) < 2:
                    st.warning("⚠️ No recent price data available.")
                else:
                    # Compute EMAs using pandas
                    hist['EMA5'] = hist['Close'].ewm(span=5, adjust=False).mean()
                    hist['EMA20'] = hist['Close'].ewm(span=20, adjust=False).mean()

                    fig = go.Figure()

                    fig.add_trace(go.Candlestick(
                        x=hist.index,
                        open=hist['Open'],
                        high=hist['High'],
                        low=hist['Low'],
                        close=hist['Close'],
                        name='Price',
                        increasing_line_color='green',
                        decreasing_line_color='red',
                        showlegend=False
                    ))

                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=hist['EMA5'],
                        mode='lines',
                        line=dict(color='blue', width=1),
                        name='EMA 5',
                        showlegend=False
                    ))

                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=hist['EMA20'],
                        mode='lines',
                        line=dict(color='orange', width=1),
                        name='EMA 20',
                        showlegend=False
                    ))

                    fig.update_layout(
                        margin=dict(l=0, r=0, t=10, b=0),
                        height=260,  # 📏 Taller chart (was ~130)
                        xaxis=dict(showticklabels=False, showgrid=False),
                        yaxis=dict(showticklabels=False, showgrid=True),
                        template="plotly_white",
                    )

                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ Failed to load chart for {row['Ticker']}. Error: {str(e)}")

