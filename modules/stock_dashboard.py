# modules/stock_dashboard.py
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from utils.openai_helper import get_stock_summary, get_risk_assessment, get_momentum_analysis, get_sentiment_analysis
import os
from textblob import TextBlob  # Ensure TextBlob is imported for sentiment analysis

USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"

# Ensure the get_analyst_ratings function is defined here
def get_analyst_ratings(ticker):
    stock = yf.Ticker(ticker)
    try:
        info = stock.info
        recommendation = info.get('recommendationKey', 'N/A').capitalize()
        number_of_analyst_opinions = info.get('numberOfAnalystOpinions', 'N/A')
        target_mean_price = info.get('targetMeanPrice', 'N/A')
        target_low_price = info.get('targetLowPrice', 'N/A')
        target_high_price = info.get('targetHighPrice', 'N/A')

        return {
            'Consensus': recommendation,
            'Number of Analyst Opinions': number_of_analyst_opinions,
            'Average Target Price': target_mean_price,
            'Low Target Price': target_low_price,
            'High Target Price': target_high_price
        }
    except Exception:
        return {
            'Consensus': 'N/A',
            'Number of Analyst Opinions': 'N/A',
            'Average Target Price': 'N/A',
            'Low Target Price': 'N/A',
            'High Target Price': 'N/A'
        }

# Web scraping function for stock-specific news
def scrape_stock_news(ticker):
    articles = []
    
    # Fetch from Yahoo Finance
    try:
        url = f'https://finance.yahoo.com/quote/{ticker}/news?p={ticker}'
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        for item in soup.find_all('h3'):
            title = item.get_text()
            link = item.find('a')['href']
            articles.append({'title': title, 'link': f'https://finance.yahoo.com{link}'})
    except Exception as e:
        print(f"Error fetching Yahoo Finance news: {e}")
    
    # Fetch from Google News
    try:
        query = f"{ticker} stock"
        url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}+when:7d&hl=en-US&gl=US&ceid=US:en"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all("item")
        for item in items[:3]:  # Limit to 3 articles
            title = item.title.text
            link = item.link.text
            articles.append({'title': title, 'link': link})
    except Exception as e:
        print(f"Error fetching Google News: {e}")
    
    # Fetch from Bloomberg
    try:
        url = f"https://www.bloomberg.com/search?query={ticker}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        articles_bloomberg = soup.select("article a")[:3]  # Limit to 3 articles
        for art in articles_bloomberg:
            title = art.get_text(strip=True)
            link = f"https://www.bloomberg.com{art['href']}"
            articles.append({'title': title, 'link': link})
    except Exception as e:
        print(f"Error fetching Bloomberg news: {e}")
    
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

# Function to get market sentiment for a specific stock
def get_stock_sentiment(ticker):
    articles = scrape_stock_news(ticker)
    sentiments = analyze_sentiment(articles)

    bullish_count = sum(1 for sentiment in sentiments if sentiment['sentiment'] == 'Bullish')
    bearish_count = sum(1 for sentiment in sentiments if sentiment['sentiment'] == 'Bearish')

    if bullish_count > bearish_count:
        sentiment_score = 7
        trend_label = 'Bullish'
    elif bearish_count > bullish_count:
        sentiment_score = 3
        trend_label = 'Bearish'
    else:
        sentiment_score = 5
        trend_label = 'Neutral'

    key_drivers = []
    if bullish_count > bearish_count:
        key_drivers.append(f"Positive sentiment surrounding {ticker} driven by news on growth prospects.")
    elif bearish_count > bullish_count:
        key_drivers.append(f"Negative sentiment on {ticker} due to concerns about earnings and market performance.")
    else:
        key_drivers.append(f"Mixed sentiment for {ticker}, no strong direction from the news.")

    return sentiment_score, trend_label, sentiments, key_drivers

def display_stock_dashboard(ticker):  # Ensure ticker is passed as a parameter
    st.markdown(f"## 📊 {ticker.upper()} Stock Dashboard (NYSE: {ticker.upper()})")

    stock = yf.Ticker(ticker)
    hist = stock.history(period="30d", interval="1h")
    info = stock.info

    # Stock Overview
    price = info.get('currentPrice') or hist['Close'].iloc[-1]
    change = info.get('regularMarketChange', 0)
    pct_change = info.get('regularMarketChangePercent', 0)
    after_hours = info.get('postMarketPrice', 'N/A')
    volume = info.get('volume', 0)
    day_low = info.get('dayLow', 'N/A')
    day_high = info.get('dayHigh', 'N/A')
    open_price = info.get('open', 'N/A')
    range_52w = f"{info.get('fiftyTwoWeekLow', 'N/A')} – {info.get('fiftyTwoWeekHigh', 'N/A')}"
    updated = datetime.now().strftime("%B %d, %Y")

    st.markdown(f"""
    ### Stock Overview  
    **Price**: ${price} | **Change**: {change:+.2f} ({pct_change:+.2f}%)  
    **After-Hours**: ${after_hours}  
    **Day Range**: {day_low} – {day_high} | **52-Week**: {range_52w}  
    **Open**: ${open_price} | **Volume**: {volume:,}  
    **Last Updated**: {updated}
    """)

    # Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Close Price'))
    fig.update_layout(
        title=f"{ticker.upper()} Price Trend",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        hovermode="x unified",
        template="plotly_white",
        height=400,
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis_rangeslider_visible=True
    )
    st.plotly_chart(fig, use_container_width=True)

    # Analyst Ratings
    st.markdown("### 🧠 Analyst Ratings")
    ratings = get_analyst_ratings(ticker)
    st.markdown(f"- **Consensus**: {ratings['Consensus']}")
    st.markdown(f"- **Number of Analyst Opinions**: {ratings['Number of Analyst Opinions']}")
    st.markdown(f"- **Average Target Price**: ${ratings['Average Target Price']}")
    st.markdown(f"- **Price Target Range**: ${ratings['Low Target Price']} – ${ratings['High Target Price']}")

    # Stock Sentiment
    st.markdown("### 🗝 Stock Sentiment Summary")
    sentiment_score, trend_label, sentiments, key_drivers = get_stock_sentiment(ticker)
    st.write(f"**Sentiment Score**: {sentiment_score} ({trend_label})")  # Corrected line
    st.write(f"**Key drivers of sentiment**:")
    for driver in key_drivers:
        st.write(f"- {driver}")

    st.markdown("### Detailed Sentiment by Article:")
    for sentiment in sentiments:
        st.write(f"- **{sentiment['title']}** (Sentiment: {sentiment['sentiment']}, Polarity: {sentiment['polarity']})")
