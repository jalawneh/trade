import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from utils.openai_helper import call_openai_chat, is_ai_enabled

def scrape_yahoo_finance():
    url = 'https://finance.yahoo.com'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    for item in soup.find_all('h3'):
        title = item.get_text()
        link = item.find('a')['href']
        articles.append({'title': title, 'link': link})
    return articles

def scrape_cnbc():
    url = 'https://www.cnbc.com'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    for item in soup.find_all('h3', class_='Card-title'):
        title = item.get_text()
        link = item.find('a')['href']
        articles.append({'title': title, 'link': link})
    return articles

def scrape_marketwatch():
    url = 'https://www.marketwatch.com'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    for item in soup.find_all('h3'):
        title = item.get_text()
        link = item.find('a')['href']
        articles.append({'title': title, 'link': link})
    return articles

def analyze_sentiment(articles):
    sentiments = []
    for article in articles:
        text = article['title']
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        sentiment = 'Neutral'
        if polarity > 0:
            sentiment = 'Bullish'
        elif polarity < 0:
            sentiment = 'Bearish'
        sentiments.append({'title': article['title'], 'sentiment': sentiment, 'polarity': polarity})
    return sentiments

def get_market_sentiment():
    articles = scrape_yahoo_finance() + scrape_cnbc() + scrape_marketwatch()
    sentiments = analyze_sentiment(articles)

    bullish_count = sum(1 for s in sentiments if s['sentiment'] == 'Bullish')
    bearish_count = sum(1 for s in sentiments if s['sentiment'] == 'Bearish')

    if bullish_count > bearish_count:
        trend_label = 'Bullish'
        sentiment_score = 7
    elif bearish_count > bullish_count:
        trend_label = 'Bearish'
        sentiment_score = 3
    else:
        trend_label = 'Neutral'
        sentiment_score = 5

    key_drivers = []
    if trend_label == 'Bullish':
        key_drivers += [
            "Positive earnings reports from major corporations indicate strong market confidence.",
            "Growth in major stock indices like S&P 500 and Nasdaq reflecting investor optimism."
        ]
    elif trend_label == 'Bearish':
        key_drivers += [
            "Increased geopolitical instability, including trade tensions and political unrest, is dampening market sentiment.",
            "High levels of volatility in the VIX indicate market fear and risk aversion."
        ]
    else:
        key_drivers.append("Mixed economic indicators, with strong GDP growth but concerns over inflation and interest rates.")

    key_drivers.append("Recent volatility in stock markets and concerns over inflation and interest rates are driving mixed sentiment.")

    return sentiment_score, trend_label, sentiments, key_drivers

def classify_stock_risk_tiers(df):
    def classify_row(volatility, ai_score):
        if volatility < 2.0 and ai_score >= 7:
            return "Low Risk"
        elif 2.0 <= volatility < 3.5 and 5 <= ai_score < 7:
            return "Medium Risk"
        else:
            return "High Risk"
    df["Risk Tier"] = df.apply(
        lambda row: classify_row(row["Volatility (%)"], row["AI Recommendation (0–10)"]),
        axis=1
    )
    return df

def show_risk_allocation():
    st.title("⚖️ Set Risk Allocation")

    st.markdown("### 🎛️ Your Risk Preferences")
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

    # --- Market Sentiment Analysis ---
    if is_ai_enabled():
        st.markdown("---")
        st.markdown("### 🤖 AI Market Sentiment")

        sentiment_score, trend_label, sentiments, key_drivers = get_market_sentiment()
        st.info(f"Sentiment Score: {sentiment_score}")
        st.info(f"Trend Label: {trend_label}")

        st.markdown("### 🗭 Sentiment Summary")
        st.write(f"The market is currently **{trend_label}** with a sentiment score of {sentiment_score}.")
        st.write("**Key Drivers:**")
        for driver in key_drivers:
            st.write(f"- {driver}")

        with st.expander("📋 Full News Breakdown"):
            for s in sentiments:
                st.write(f"- **{s['title']}** (Sentiment: {s['sentiment']}, Polarity: {s['polarity']:.2f})")

        if sentiment_score < 4:
            st.warning("📉 Bearish market — consider reducing exposure to high-risk assets.")
        elif sentiment_score > 6:
            st.success("📈 Bullish market — higher-risk positions may be rewarded.")
        else:
            st.info("⚖️ Neutral market — maintain a balanced risk distribution.")

    # --- Risk Tier Classification ---
    if 'top10' not in st.session_state:
        st.warning("⚠️ Please run the Market Scan first.")
        return

    df = st.session_state.get("top10", pd.DataFrame())

    # ✅ Strip and normalize column names
    df.columns = (
        df.columns.str.encode("ascii", "ignore").str.decode("ascii")
        .str.strip()
        .str.replace("\u00a0", " ")
        .str.replace("–", "-")
        .str.replace("—", "-")
        .str.replace(r"[^a-zA-Z0-9 ()%-]", "", regex=True)
    )

    # Attempt to rename damaged columns
    for col in df.columns:
        if "AI Recommendation" in col and "10" in col:
            df.rename(columns={col: "AI Recommendation (0-10)"}, inplace=True)
        if "Last Close" in col:
            df.rename(columns={col: "Last Close ($)"}, inplace=True)

    # Check required columns
    if not all(col in df.columns for col in ["Volatility (%)", "AI Recommendation (0-10)"]):
        st.error("❌ One or both required columns are missing from the DataFrame.")
        return

    if df.empty:
        st.warning("⚠️ No market scan results found. Please run the Market Scan first.")
        return

    required_columns = ["Volatility (%)", "AI Recommendation (0-10)"]
    for col in required_columns:
        if col not in df.columns:
            st.error(f"❌ Required column missing: {col}")
            return
        if df[col].isnull().all():
            st.error(f"❌ Column {col} contains only null values.")
            return

    st.markdown("---")
    st.markdown("### 📊 Risk Classification of Candidates")

    def classify_stock_risk_tiers(df):
        def classify_row(volatility, ai_score):
            if volatility < 2.0 and ai_score >= 7:
                return "Low"
            elif 2.0 <= volatility < 3.5 and 5 <= ai_score < 7:
                return "Medium"
            else:
                return "High"

        df["Risk Tier"] = df.apply(
            lambda row: classify_row(row["Volatility (%)"], row["AI Recommendation (0-10)"]),
            axis=1
        )
        return df

    classified = classify_stock_risk_tiers(df)
    st.session_state['allocated_stocks'] = classified

    COLOR_MAP = {
        "Low": "#D1E7DD",       # Light green
        "Medium": "#FFF3CD",    # Light yellow
        "High": "#F8D7DA"       # Light red
    }

    for tier in ['Low', 'Medium', 'High']:
        group = classified[classified['Risk Tier'] == tier]
        st.markdown(f"#### {tier} Risk Stocks ({len(group)})")
        if group.empty:
            st.write("- None")
        else:
            styled = group[['Ticker', 'Company Name', 'AI Recommendation (0-10)', 'Volatility (%)', 'Score']].style.apply(
                lambda _: [f"background-color: {COLOR_MAP[tier]}"] * 5,
                axis=1
            )
            st.dataframe(styled, use_container_width=True)

    st.success("✅ Stocks classified into risk tiers and ready for allocation!")
