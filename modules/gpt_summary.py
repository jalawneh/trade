# modules/gpt_summary.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
import pytz
import datetime
from serpapi import GoogleSearch

def show_gpt_summary():
    st.title("📰 Market News Summary")

    central = pytz.timezone("US/Central")
    now = datetime.datetime.now(central)
    now_str = now.strftime('%B %d, %Y at %I:%M %p %Z')
    today = now.date()

    st.info(f"🕒 Fetching market-moving news for {today}...")

    headers = {'User-Agent': 'Mozilla/5.0'}
    all_headlines = []

    def parse_source(url, selector, source_name, prefix="https://", rss=False):
        try:
            r = requests.get(url, headers=headers)
            r.raise_for_status()
            if rss:
                soup = BeautifulSoup(r.content, features="xml")
                items = soup.find_all("item")[:10]
                for item in items:
                    headline = item.title.text
                    link = item.link.text
                    pub_date = parsedate_to_datetime(item.pubDate.text).astimezone(central)
                    if (now - pub_date).total_seconds() <= 86400:
                        all_headlines.append((headline, link, source_name, pub_date.strftime('%Y-%m-%d %I:%M %p %Z')))
            else:
                soup = BeautifulSoup(r.text, "html.parser")
                articles = soup.select(selector)[:20]
                for a in articles:
                    headline = a.get_text(strip=True)
                    href = a.get("href")
                    link = href if href.startswith("http") else prefix + href
                    all_headlines.append((headline, link, source_name, now.strftime('%Y-%m-%d %I:%M %p %Z')))
        except Exception as e:
            st.warning(f"{source_name} error: {e}")

    parse_source("https://finance.yahoo.com/news/", "li.js-stream-content h3 a", "Yahoo Finance", "https://finance.yahoo.com")
    parse_source("https://www.cnbc.com/markets/", "a.Card-title", "CNBC")
    parse_source("https://news.google.com/rss/search?q=site:reuters.com+business&hl=en-US&gl=US&ceid=US:en", "", "Reuters", rss=True)
    parse_source("https://www.bloomberg.com/markets", "a[data-testid='StoryModuleHeadlineLink']", "Bloomberg", "https://www.bloomberg.com")

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
        st.warning(f"Google News error: {e}")

    key_terms = ["fed", "inflation", "rate", "earnings", "geopolitical", "jobs", "cpi", "gdp", "conflict", "oil"]
    relevant = [(h, l, src, t) for h, l, src, t in all_headlines if any(k in h.lower() for k in key_terms)]

    st.markdown("### 🧠 Summary")
    st.markdown(f"**Report Generated:** {now_str}")
    display_list = relevant if relevant else all_headlines

    if display_list:
        st.markdown("\n".join([f"- [{h}]({l}) ({src}, {t})" for h, l, src, t in display_list[:10]]))
    else:
        st.markdown("❌ No headlines retrieved.")
