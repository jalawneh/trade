# utils/openai_helper.py
import os
import requests
import re
import streamlit as st
import json
from dotenv import load_dotenv

load_dotenv()

USE_OPENAI = os.getenv("USE_OPENAI", "true").lower() == "true"

def call_openai_chat(prompt):
    import streamlit as st  # Ensure this is imported

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not USE_OPENAI:
        return ""  # Skip if API not set or disabled

    model = st.session_state.get("gpt_model", "gpt-3.5-turbo")  # 🧠 Use selected model

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
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
    You are an elite real-time day trading analyst AI. Based on the most current intraday data, analyze this stock and assess its suitability for a same-day profit trade. Use live volume, momentum, volatility, and potential catalysts (news or chart patterns) to support your evaluation.

    Stock Details:
    - Ticker: {row['Ticker']}
    - Company: {row['Company Name']}
    - Sector: {row['Sector']}
    - Volume: {row['Volume']}
    - Change: {row['Change (%)']}%
    - Volatility: {row['Volatility (%)']}%

    Perform the following:

    1. Identify why this stock is active today (mention chart patterns, momentum signals, or recent news/catalyst).
    2. Evaluate risk profile: discuss liquidity, volatility, price support/resistance, and risk/reward potential.
    3. Suggest which type of trader would benefit (e.g., scalper, momentum trader, range-bound trader).
    4. Give a final recommendation score (0–10) based on setup strength, news, volume confirmation, and risk profile.

    Respond in JSON with keys:
    - "why": string
    - "risk": string
    - "who_benefits": string
    - "score": integer (0–10)
    """
    response = call_openai_chat(prompt)
    match = re.search(r"score.*?(\d{1,2})", response, re.IGNORECASE)
    score = int(match.group(1)) if match else 0
    return response, min(score, 10)

def analyze_stock_summary_and_details(row):
    prompt = f"""
You are an elite real-time day trading analyst AI. Analyze the stock below using the most current intraday data and return:

1. A one-sentence summary with a sentiment tag for dashboard display.
2. A detailed breakdown including:
   - Why it's active
   - Risk profile
   - Who benefits
   - Final recommendation score (0–10)

Also include a plain-language score label based on this scale:
- 0–3: "Avoid"
- 4–5: "Caution"
- 6–7: "Moderate Opportunity"
- 8–10: "Strong Buy"

Stock Details:
- Ticker: {row['Ticker']}
- Company: {row['Company Name']}
- Sector: {row['Sector']}
- Volume: {row['Volume']}
- Change: {row['Change (%)']}%
- Volatility: {row['Volatility (%)']}%

Respond only in this JSON format:
{{
  "summary": "🔼 Bullish – ...",
  "why": "...",
  "risk": "...",
  "who_benefits": "...",
  "score": 0–10,
  "score_label": "Avoid | Caution | Moderate Opportunity | Strong Buy"
}}
"""
    response = call_openai_chat(prompt)
    try:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        data = json.loads(match.group(0)) if match else {}
        score = min(int(data.get("score", 0)), 10)

        label_map = {
            "Avoid": "🔴 Avoid",
            "Caution": "⚠️ Caution",
            "Moderate Opportunity": "🟡 Moderate Opportunity",
            "Strong Buy": "🟢 Strong Buy"
        }
        score_label = data.get("score_label", "")
        tagged_label = label_map.get(score_label, score_label)

        # Only return clean summary and breakdown
        summary = data.get("summary", "⚠️ No summary")
        ai_notes = f"📘 Why:\n{data.get('why','')}\n\n📉 Risk:\n{data.get('risk','')}\n\n🎯 Who Benefits:\n{data.get('who_benefits','')}\n\n🏁 Score: {score} – {tagged_label}"

        return {
            "summary": summary,
            "ai_notes": ai_notes,
            "score": score,
            "score_label": tagged_label
        }
    except Exception as e:
        return {
            "summary": "⚠️ Analysis unavailable.",
            "ai_notes": f"Error: {str(e)}",
            "score": 0,
            "score_label": "🔴 Avoid"
        }


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
