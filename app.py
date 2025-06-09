import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import re
import matplotlib.pyplot as plt

# --- MUST BE FIRST ---
st.set_page_config(page_title="Day Trading Scanner", layout="wide")

st.markdown("<h1 style='text-align: center; font-size: 60px;'>📈 Day Trader AI Agent</h1>", unsafe_allow_html=True)

# --- OpenAI API ---
OPENAI_API_KEY = "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"  # Replace with your actual key

def call_openai_chat(prompt):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Error: {e}"

# --- Session Defaults ---
def init_allocation_state():
    st.session_state.setdefault('low_risk', 60)
    st.session_state.setdefault('med_risk', 30)
    st.session_state.setdefault('high_risk', 10)

# --- Risk Allocation ---
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

# --- Profit Plan ---
def show_profit_plan():
    st.title("💰 Generate Profit Plan")
    if 'top10' not in st.session_state:
        st.warning("You must run the market scan first.")
        return

    top10 = st.session_state['top10']
    target = 100
    budget = 3000
    low_pct = st.session_state.low_risk
    med_pct = st.session_state.med_risk
    high_pct = st.session_state.high_risk

    budgets = {
        'low': budget * low_pct / 100,
        'med': budget * med_pct / 100,
        'high': budget * high_pct / 100
    }

    st.info(f"💼 Allocation: Low {low_pct}%, Med {med_pct}%, High {high_pct}%")
    fig, ax = plt.subplots()
    ax.pie(budgets.values(), labels=budgets.keys(), autopct='%1.1f%%')
    st.pyplot(fig)

    top10['Risk Score'] = top10.apply(lambda r: (10 - r['AI Recommendation (0–10)']) + r['Volatility (%)'] / 10, axis=1)
    top10['Risk Tier'] = top10['Risk Score'].apply(lambda s: 'low' if s <= 4 else 'med' if s <= 6 else 'high')

    spent = {t: 0 for t in budgets}
    profit = {t: 0 for t in budgets}
    plan = []
    total_spent = total_profit = 0

    for tier in ['low', 'med', 'high']:
        df_tier = top10[top10['Risk Tier'] == tier].sort_values('AI Recommendation (0–10)', ascending=False)
        tier_budget = budgets[tier]

        for _, r in df_tier.iterrows():
            price = r['Last Close ($)']
            move = max(3, r['Volatility (%)']) / 2
            max_shares = int((tier_budget - spent[tier]) / price)
            if max_shares <= 0:
                continue

            invest = max_shares * price
            sell_price = price * (1 + move / 100)
            prof = (sell_price - price) * max_shares
            roi = prof / invest if invest > 0 else 0

            if prof < 5 or roi < 0.02 or invest < 50:
                continue

            spent[tier] += invest
            profit[tier] += prof
            total_spent += invest
            total_profit += prof
            plan.append({
                'Ticker': r['Ticker'], 'Buy': round(price, 2), 'Sell': round(sell_price, 2),
                'Shares': max_shares, 'Invest': round(invest, 2), 'Profit': round(prof, 2),
                'AI Score': r['AI Recommendation (0–10)'],
                'Volatility %': r['Volatility (%)'],
                'Risk Tier': tier.capitalize()
            })

            if total_profit >= target:
                break

    df = pd.DataFrame(plan)

    st.markdown("### 📊 Profit Plan Summary")
    if total_profit < target:
        st.warning(f"⚠️ Only ${total_profit:.2f} profit (< ${target} goal)")
    else:
        st.success(f"🎯 Goal Met: ${total_profit:.2f} profit using ${total_spent:.2f}")

    st.dataframe(df, use_container_width=True)

    fig2, ax2 = plt.subplots()
    ax2.bar(profit.keys(), profit.values())
    ax2.set_title("Profit by Tier")
    st.pyplot(fig2)



# --- Fetch Yahoo Finance Movers ---
@st.cache_data(ttl=900)
def fetch_movers():
    def get_yahoo_table(url):
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            return pd.read_html(r.text)[0]
        except:
            return pd.DataFrame()
    return pd.concat([
        get_yahoo_table("https://finance.yahoo.com/gainers"),
        get_yahoo_table("https://finance.yahoo.com/losers"),
        get_yahoo_table("https://finance.yahoo.com/most-active")
    ]).drop_duplicates(subset="Symbol")["Symbol"].tolist()

# --- Analyze Single Stock ---
def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d", interval="1h")
        if len(hist) < 2:
            return None
        last_close = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        volume = hist['Volume'].iloc[-1]
        volatility = ((hist['High'] - hist['Low']) / hist['Close']).mean() * 100
        info = stock.info
        return {
            "Ticker": ticker,
            "Company Name": re.sub(r'<.*?>', '', info.get('shortName', 'N/A')),
            "Previous Close ($)": round(prev_close, 2),
            "Last Close ($)": round(last_close, 2),
            "Change (%)": round(((last_close - prev_close) / prev_close) * 100, 2),
            "Volume": int(volume),
            "Volatility (%)": round(volatility, 2),
            "Sector": info.get('sector', 'N/A')
        }
    except:
        return None

# --- Scan Market Function ---
def scan_market():
    import concurrent.futures

    with st.spinner("Scanning market and analyzing stocks..."):
        tickers = fetch_movers()

        # Parallelize analysis
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(analyze_stock, tickers))

        # Strict filter first
        results = [r for r in results if r and r["Volume"] > 1_000_000 and r["Volatility (%)"] > 3 and 1 < r["Last Close ($)"] < 200]

        # Relax filter if too few results
        if len(results) < 10:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                relaxed_results = list(executor.map(analyze_stock, tickers))
            results = [r for r in relaxed_results if r and r["Volume"] > 500_000 and r["Volatility (%)"] > 2 and 0.5 < r["Last Close ($)"] < 300]

        df = pd.DataFrame(results)

        if df.empty:
            st.warning("No qualifying stocks found.")
            return

        df['Score'] = (
            df["Change (%)"].abs() * 0.5 +
            df["Volatility (%)"] * 0.3 +
            (df["Volume"] / 1_000_000) * 0.2
        )

        df['AI Recommendation (0–10)'] = 0
        df['AI Notes'] = ""

        # GPT prompt generation and score extraction
        def get_ai_analysis(row):
            prompt = f"""
You are an elite day trader AI. Analyze this stock briefly:

- Ticker: {row['Ticker']}
- Company: {row['Company Name']}
- Sector: {row['Sector']}
- Volume: {row['Volume']}
- Change: {row['Change (%)']}%
- Volatility: {row['Volatility (%)']}%

Reply concisely with:
1. Why it was picked.
2. Why score and volatility matter.
3. Who the trade fits.
4. Final score (0–10).
"""
            ai_text = call_openai_chat(prompt)
            match = re.search(r"score.*?(\d{1,2})", ai_text, re.IGNORECASE)
            score = int(match.group(1)) if match else 0
            return ai_text, min(score, 10)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            gpt_results = list(executor.map(get_ai_analysis, [row for _, row in df.iterrows()]))

        for i, (ai_text, score) in enumerate(gpt_results):
            df.at[i, 'AI Notes'] = ai_text
            df.at[i, 'AI Recommendation (0–10)'] = score

        top5 = df.sort_values(by="AI Recommendation (0–10)", ascending=False).head(15)
        st.session_state['top10'] = top5
        st.success("Top 15 Stocks Identified ✅")
        st.dataframe(top5, use_container_width=True)

        for i, row in top5.reset_index().iterrows():
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader(f"{i+1}. {row['Ticker']} - {row['Company Name']}")
                st.markdown(f"**Sector**: {row['Sector']}  \\n**Volume**: {row['Volume']:,}  \\n**Change**: {row['Change (%)']}%  \\n**Volatility**: {row['Volatility (%)']}%  \\n**AI Score**: {row['AI Recommendation (0–10)']}")
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
                if st.button(f"📊 Full Chart", key=f"chart_{row['Ticker']}"):
                    hist_full = yf.Ticker(row['Ticker']).history(period="14d", interval="30m")
                    with st.expander(f"📈 Full Chart: {row['Ticker']}", expanded=True):
                        fig_big, ax_big = plt.subplots(figsize=(10, 4))
                        ax_big.plot(hist_full.index, hist_full['Close'])
                        ax_big.set_title(f"{row['Ticker']} - Last 14 Days (30m)")
                        ax_big.grid(True)
                        st.pyplot(fig_big)
            st.markdown("---")

# --- GPT Summary ---
def show_gpt_summary():
    st.title("🤖 GPT Market Summary")
    with st.spinner("Calling GPT..."):
        prompt = "Give a 2-line summary of today's US stock market outlook."
        result = call_openai_chat(prompt)
        st.markdown("### 🧠 GPT Output")
        st.write(result)


# --- Main Page Title ---
st.markdown(
    "<div style='text-align: center; font-size: 18px;'>"
    "Welcome! Use the sidebar to begin scanning the market, set your risk preferences, or generate a profit plan."
    "</div>",
    unsafe_allow_html=True
)

# --- Sidebar Menu ---
st.sidebar.title("📂 Navigation")
choice = st.sidebar.radio(
    "Choose Option",
    ["-- Select an Action --", "Scan Market", "Risk Allocation", "Generate Profit Plan", "GPT Market Summary"]
)

# --- Session Initialization ---
def init_allocation_state():
    st.session_state.setdefault('low_risk', 60)
    st.session_state.setdefault('med_risk', 30)
    st.session_state.setdefault('high_risk', 10)

init_allocation_state()

# --- Actions ---
if choice == "Scan Market":
    scan_market()

elif choice == "Risk Allocation":
    show_risk_allocation()

elif choice == "Generate Profit Plan":
    show_profit_plan()

elif choice == "GPT Market Summary":
    with st.spinner("Calling GPT..."):
        result = call_openai_chat("Give a 2-line summary of today's US stock market outlook.")
        st.subheader("🧠 GPT Market Summary")
        st.write(result)

# Note: do not execute any action if "-- Select an Action --" is chosen

