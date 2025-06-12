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

def show_profit_plan():
    st.title("💰 Generate Profit Plan")
    if 'top10' not in st.session_state:
        st.warning("You must run the market scan first.")
        return

    top10 = st.session_state['top10'].copy()
    target = 100
    budget = 3000
    total_spent = 0
    total_profit = 0
    plan = []

    # Compute risk score and profit potential
    top10['Risk Score'] = top10.apply(
        lambda r: (10 - r['AI Recommendation (0–10)']) + r['Volatility (%)'] / 10, axis=1)
    top10['Profit Potential'] = top10.apply(
        lambda r: (max(3, r['Volatility (%)']) / 2) * r['Last Close ($)'] / 100, axis=1)

    # Sort by lowest risk and highest profit potential
    top10_sorted = top10.sort_values(by=['Risk Score', 'Profit Potential'], ascending=[True, False])

    used_tickers = set()

    for _, r in top10_sorted.iterrows():
        if total_profit >= target or total_spent >= budget:
            break

        price = r['Last Close ($)']
        move = max(3, r['Volatility (%)']) / 2
        max_shares = int((budget - total_spent) / price)
        if max_shares <= 0:
            continue

        invest = max_shares * price
        sell_price = price * (1 + move / 100)
        prof = (sell_price - price) * max_shares
        roi = prof / invest if invest > 0 else 0

        if prof < 5 or roi < 0.02 or invest < 50:
            continue

        total_spent += invest
        total_profit += prof
        used_tickers.add(r['Ticker'])

        plan.append({
            'Ticker': r['Ticker'], 'Buy': round(price, 2), 'Sell': round(sell_price, 2),
            'Shares': max_shares, 'Invest': round(invest, 2), 'Profit': round(prof, 2),
            'AI Score': r['AI Recommendation (0–10)'],
            'Volatility %': r['Volatility (%)'],
            'Risk Score': round(r['Risk Score'], 2)
        })

    df = pd.DataFrame(plan)

    st.markdown("### 📊 Profit Plan Summary")
    if total_profit < target:
        st.warning(f"⚠️ Only ${total_profit:.2f} profit (< ${target} goal)")
    else:
        st.success(f"🌟 Goal Met: ${total_profit:.2f} profit using ${total_spent:.2f}")

    st.dataframe(df, use_container_width=True)

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

import datetime
import streamlit as st
import requests
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
import pytz
from serpapi import GoogleSearch

# --- Market Headlines Summary from Yahoo, CNBC, Reuters, Bloomberg, Google News ---
def show_gpt_summary():
    st.title("\U0001F4F0 Market News Summary")

    central = pytz.timezone("US/Central")
    now = datetime.datetime.now(central)
    now_str = now.strftime('%B %d, %Y at %I:%M %p %Z')
    today = now.date()

    st.info(f"\U0001F553 Searching for U.S. market-moving news for {today}...")

    headers = {'User-Agent': 'Mozilla/5.0'}
    all_headlines = []

    # --- Yahoo Finance ---
    try:
        r1 = requests.get("https://finance.yahoo.com/news/", headers=headers)
        r1.raise_for_status()
        soup1 = BeautifulSoup(r1.text, "html.parser")
        articles = soup1.select("li.js-stream-content")[:20]
        for art in articles:
            title_tag = art.select_one("h3 a")
            time_tag = art.select_one("time")
            if title_tag and title_tag.has_attr("href"):
                headline = title_tag.get_text(strip=True)
                link = "https://finance.yahoo.com" + title_tag['href']
                timestamp_raw = time_tag["datetime"] if time_tag and time_tag.has_attr("datetime") else None
                try:
                    timestamp = datetime.datetime.fromisoformat(timestamp_raw.replace('Z', '+00:00')).astimezone(central) if timestamp_raw else now
                except:
                    timestamp = now
                if (now - timestamp).total_seconds() <= 86400:
                    all_headlines.append((headline, link, "Yahoo Finance", timestamp.strftime('%Y-%m-%d %I:%M %p %Z')))
    except Exception as e:
        st.warning(f"Yahoo scrape error: {e}")

    # --- CNBC ---
    try:
        r2 = requests.get("https://www.cnbc.com/markets/", headers=headers)
        r2.raise_for_status()
        soup2 = BeautifulSoup(r2.text, "html.parser")
        articles = soup2.select("a.Card-title")[:20]
        for a in articles:
            headline = a.get_text(strip=True)
            link = a['href'] if a.has_attr("href") else "https://www.cnbc.com/markets/"
            timestamp = now
            all_headlines.append((headline, link, "CNBC", timestamp.strftime('%Y-%m-%d %I:%M %p %Z')))
    except Exception as e:
        st.warning(f"CNBC scrape error: {e}")

    # --- Reuters via Google News RSS fallback ---
    try:
        rss_url = "https://news.google.com/rss/search?q=site:reuters.com+business&hl=en-US&gl=US&ceid=US:en"
        r3 = requests.get(rss_url, headers=headers)
        r3.raise_for_status()
        soup3 = BeautifulSoup(r3.content, features="xml")
        items = soup3.find_all("item")[:10]
        for item in items:
            headline = item.title.text
            link = item.link.text
            pub_date = parsedate_to_datetime(item.pubDate.text).astimezone(central)
            if (now - pub_date).total_seconds() <= 86400:
                all_headlines.append((headline, link, "Reuters (via Google News)", pub_date.strftime('%Y-%m-%d %I:%M %p %Z')))
    except Exception as e:
        st.warning(f"Reuters RSS fallback error: {e}")

    # --- Bloomberg ---
    try:
        r4 = requests.get("https://www.bloomberg.com/markets", headers=headers)
        r4.raise_for_status()
        soup4 = BeautifulSoup(r4.text, "html.parser")
        articles = soup4.select("a[data-testid='StoryModuleHeadlineLink']")[:20]
        for a in articles:
            headline = a.get_text(strip=True)
            link = "https://www.bloomberg.com" + a['href'] if a.has_attr("href") else "https://www.bloomberg.com/markets"
            timestamp = now
            all_headlines.append((headline, link, "Bloomberg", timestamp.strftime('%Y-%m-%d %I:%M %p %Z')))
    except Exception as e:
        st.warning(f"Bloomberg scrape error: {e}")

    # --- Google News via SerpAPI ---
    try:
        serpapi_key = "c4e703d9f24d9f5aafe8e587286bf44e78295385165f5f42744904eab142d337"
        if serpapi_key:
            params = {
                "engine": "google_news",
                "q": f"US stock market {today}",
                "api_key": serpapi_key
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            for article in results.get("news_results", [])[:10]:
                title = article.get("title")
                link = article.get("link")
                source = article.get("source")
                date_str = article.get("date") or now_str
                all_headlines.append((title, link, f"Google News ({source})", date_str))
    except Exception as e:
        st.warning(f"Google News search error: {e}")

    # Filter and summarize
    key_terms = ["fed", "inflation", "rate", "earnings", "geopolitical", "jobs", "cpi", "gdp", "conflict", "oil"]
    relevant = [(h, l, src, t) for h, l, src, t in all_headlines if any(k in h.lower() for k in key_terms)]

    st.markdown("### \U0001F9E0 Summary")
    st.markdown(f"**Report Generated:** {now_str}")

    if relevant:
        st.markdown("\n".join([f"- [{h}]({l}) ({src}, {t})" for h, l, src, t in relevant[:10]]))
    elif all_headlines:
        st.markdown("No keyword matches. Top general headlines:")
        st.markdown("\n".join([f"- [{h}]({l}) ({src}, {t})" for h, l, src, t in all_headlines[:10]]))
    else:
        st.markdown("❌ No headlines retrieved.")

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
    show_gpt_summary()

# Note: do not execute any action if "-- Select an Action --" is chosen

