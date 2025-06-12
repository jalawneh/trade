# modules/scan_utils.py

import pandas as pd
import yfinance as yf
import re
import requests
from io import StringIO

def fetch_movers():
    def get_yahoo_table(url, slices=2):
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            r.raise_for_status()
            tables = pd.read_html(StringIO(r.text))
            df = pd.concat(tables[:slices]) if slices <= len(tables) else tables[0]
            return df
        except:
            return pd.DataFrame()

    all_sources = [
        "https://finance.yahoo.com/gainers",
        "https://finance.yahoo.com/losers",
        "https://finance.yahoo.com/most-active",
        "https://finance.yahoo.com/screener/pre-market",
        "https://finance.yahoo.com/screener/new-highs"
    ]

    all_symbols = []
    for url in all_sources:
        table = get_yahoo_table(url, slices=3)
        if not table.empty and "Symbol" in table.columns:
            all_symbols.extend(table["Symbol"].tolist())

    tickers = list(set(s for s in all_symbols if isinstance(s, str) and s.isupper() and 1 <= len(s) <= 6))
    return tickers

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
