import streamlit as st
from utils.openai_helper import call_openai_chat, is_ai_enabled
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob

# Define a dictionary of scraping functions for different sites
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

# Sentiment analysis function
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

# Function to scrape from multiple sources and perform sentiment analysis
def get_market_sentiment():
    # Scrape articles from multiple sources
    articles = []
    articles.extend(scrape_yahoo_finance())
    articles.extend(scrape_cnbc())
    articles.extend(scrape_marketwatch())
    
    # Add more scraping calls here for additional sites...

    # Analyze sentiment
    sentiments = analyze_sentiment(articles)

    # Summarize sentiment
    bullish_count = sum(1 for sentiment in sentiments if sentiment['sentiment'] == 'Bullish')
    bearish_count = sum(1 for sentiment in sentiments if sentiment['sentiment'] == 'Bearish')

    # Provide final sentiment score and trend
    if bullish_count > bearish_count:
        trend_label = 'Bullish'
        sentiment_score = 7
    elif bearish_count > bullish_count:
        trend_label = 'Bearish'
        sentiment_score = 3
    else:
        trend_label = 'Neutral'
        sentiment_score = 5

    # Expanded market insights (key drivers)
    key_drivers = []
    if bullish_count > bearish_count:
        key_drivers.append("Positive earnings reports from major corporations indicate strong market confidence.")
        key_drivers.append("Growth in major stock indices like S&P 500 and Nasdaq reflecting investor optimism.")
    elif bearish_count > bullish_count:
        key_drivers.append("Increased geopolitical instability, including trade tensions and political unrest, is dampening market sentiment.")
        key_drivers.append("High levels of volatility in the VIX indicate market fear and risk aversion.")
    else:
        key_drivers.append("Mixed economic indicators, with strong GDP growth but concerns over inflation and interest rates.")
    
    # Additional insights: Volatility, Earnings Reports, Economic Indicators
    key_drivers.append("Recent volatility in stock markets and concerns over inflation and interest rates are driving mixed sentiment.")

    return sentiment_score, trend_label, sentiments, key_drivers

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

        # Get sentiment analysis based on scraped news
        sentiment_score, trend_label, sentiments, key_drivers = get_market_sentiment()
        
        # Display sentiment analysis results
        st.info(f"Sentiment Score: {sentiment_score}")
        st.info(f"Trend Label: {trend_label}")
        st.markdown("### 🗭 Sentiment Summary")
        
        # Add a detailed summary of the sentiment
        st.write(f"Sentiment Score of {sentiment_score} suggests a {trend_label} market.")
        st.write(f"Key drivers of sentiment include:")
        for driver in key_drivers:
            st.write(f"- {driver}")

        st.markdown("### Detailed Sentiment by Article:")
        for sentiment in sentiments:
            st.write(f"- **{sentiment['title']}** (Sentiment: {sentiment['sentiment']}, Polarity: {sentiment['polarity']})")

        # Provide more detailed suggestions based on sentiment
        if sentiment_score < 4:
            st.warning("Market sentiment is bearish. Consider reducing exposure to high-risk assets and increasing allocation to safe-haven assets.")
        elif sentiment_score > 6:
            st.success("Market sentiment is bullish. Consider increasing allocation to higher-risk, higher-reward assets.")
        else:
            st.info("Market sentiment is neutral. Maintain balanced risk allocation or wait for clearer signals.")
