# modules/stock_dashboard.py
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from utils.openai_helper import get_stock_summary, get_risk_assessment, get_momentum_analysis, get_sentiment_analysis


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


def get_sentiment_summary(ticker):
    try:
        response = requests.get(f'https://api.swaggystocks.com/api/v1/sentiment/{ticker}')
        data = response.json()
        sentiment_score = data.get('sentiment_score', 'N/A')
        sentiment_trend = data.get('sentiment_trend', 'N/A')

        return {
            'Sentiment Score': sentiment_score,
            'Sentiment Trend': sentiment_trend
        }
    except Exception:
        return {
            'Sentiment Score': 'N/A',
            'Sentiment Trend': 'N/A'
        }


def fetch_news_headlines(ticker):
    headlines = []
    try:
        # Google News RSS
        query = ticker + " stock"
        url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}+when:7d&hl=en-US&gl=US&ceid=US:en"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all("item")
        headlines += [(item.title.text, item.link.text) for item in items[:3]]
    except:
        pass

    try:
        # Bloomberg Fallback
        url = f"https://www.bloomberg.com/search?query={ticker}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        articles = soup.select("article a")[:3]
        for art in articles:
            title = art.get_text(strip=True)
            link = "https://www.bloomberg.com" + art['href']
            headlines.append((title, link))
    except:
        pass

    return headlines


def display_stock_dashboard(ticker):
    st.markdown(f"## 📊 {ticker.upper()} Stock Dashboard (NYSE: {ticker.upper()})")

    stock = yf.Ticker(ticker)
    hist = stock.history(period="5d", interval="1h")
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

    # Sentiment Summary
    st.markdown("### 🗝 Sentiment Summary")
    sentiment = get_sentiment_summary(ticker)
    st.markdown(f"- **Sentiment Score**: {sentiment['Sentiment Score']}")
    st.markdown(f"- **Sentiment Trend**: {sentiment['Sentiment Trend']}")

    # AI Summary
    st.markdown("### 🤖 AI Insights")
    ai_summary = get_stock_summary(ticker, f"Price={price}, Volatility={info.get('beta', 'N/A')}, Sector={info.get('sector', 'N/A')}")
    st.markdown(ai_summary)

    # News
    st.markdown("### 📰 Recent News")
    news_items = fetch_news_headlines(ticker)
    if news_items:
        for title, link in news_items:
            st.markdown(f"- [{title}]({link})")
    else:
        st.info("News currently unavailable.")
