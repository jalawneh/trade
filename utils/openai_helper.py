# utils/openai_helper.py
import os
import requests
import re
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

USE_OPENAI = os.getenv("USE_OPENAI", "true").lower() == "true"

def call_openai_chat(prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not USE_OPENAI:
        return ""  # Skip if API not set or disabled

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError:
        return ""
    except Exception:
        return ""

def generate_ai_score(row):
    prompt = f"""
    You are an elite day trading assistant. Analyze this stock:

    - Ticker: {row['Ticker']}
    - Company: {row['Company Name']}
    - Sector: {row['Sector']}
    - Volume: {row['Volume']}
    - Change: {row['Change (%)']}%
    - Volatility: {row['Volatility (%)']}%

    Respond Briefly with:
    1. Why picked
    2. Risk relevance
    3. Who benefits
    4. Final recommendation score (0–10)
    """
    response = call_openai_chat(prompt)
    match = re.search(r"score.*?(\d{1,2})", response, re.IGNORECASE)
    score = int(match.group(1)) if match else 0
    return response, min(score, 10)

def get_stock_summary(ticker, details):
    prompt = f"""
    Provide a brief trading summary for {ticker} given:
    {details}

    Respond with key highlights including catalysts, resistance/support levels, and trend direction.
    """
    return call_openai_chat(prompt)

def get_risk_assessment(ticker, volatility, sector):
    prompt = f"""
    Analyze the risk profile of {ticker} in the {sector} sector. Volatility is {volatility}%.
    Consider industry factors, typical volatility ranges, and trading conditions.
    Provide a summary of the risk exposure.
    """
    return call_openai_chat(prompt)

def get_momentum_analysis(ticker, change_pct, volume):
    prompt = f"""
    Analyze the momentum of {ticker}:
    - % Change: {change_pct}%
    - Volume: {volume}

    Indicate if momentum is building or fading, and whether volume supports a move.
    """
    return call_openai_chat(prompt)

def get_sentiment_analysis(news_headlines):
    prompt = f"""
    Based on these recent headlines:
    {news_headlines}

    Summarize market sentiment for this stock. Use a tone indicator (e.g., Bullish, Neutral, Bearish).
    """
    return call_openai_chat(prompt)

def get_final_score_justification(details):
    prompt = f"""
    Using this trading analysis data:
    {details}

    Justify the final recommendation score (0–10) and identify key influencing factors.
    """
    return call_openai_chat(prompt)

def is_ai_enabled():
    from dotenv import load_dotenv
    load_dotenv()
    env_flag = os.getenv("USE_OPENAI", "false").lower() == "true"
    ui_flag = st.session_state.get("use_ai", True)
    return env_flag and ui_flag
