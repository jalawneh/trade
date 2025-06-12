# modules/profit_plan.py

import streamlit as st
import pandas as pd
import time
from modules.scan_utils import fetch_movers, analyze_stock

def show_profit_plan():
    st.title("💰 Smart Profit Plan")

    def get_ranked_candidates():
        top = st.session_state['top10']
        top['Risk Score'] = top.apply(lambda r: (10 - r['AI Recommendation (0–10)']) + r['Volatility (%)'] / 10, axis=1)
        return top.sort_values(by=['Risk Score', 'AI Recommendation (0–10)'], ascending=[True, False]).copy()

    candidates = get_ranked_candidates()
    plan, total_spent, total_profit = simulate_plan(candidates)

    if plan:
        st.subheader("📊 Profit Plan")
        st.write(f"Total Investment: ${total_spent:.2f}")
        st.write(f"Expected Profit: ${total_profit:.2f}")
        st.dataframe(pd.DataFrame(plan))
    else:
        st.warning("⚠️ Unable to generate a profit plan with the current data.")

def simulate_plan(candidates, budget=3000, target_profit=100):
    plan = []
    total_spent = total_profit = 0
    used_tickers = set()
    full_pool = candidates.copy()
    attempt = 0
    max_attempts = 5

    while attempt < max_attempts:
        for _, row in full_pool.iterrows():
            if row['Ticker'] in used_tickers:
                continue

            price = row['Last Close ($)']
            volatility = max(3, row['Volatility (%)']) / 2
            max_shares = int((budget - total_spent) / price)

            if max_shares <= 0:
                continue

            invest = max_shares * price
            sell_price = price * (1 + volatility / 100)
            profit = (sell_price - price) * max_shares
            roi = profit / invest if invest > 0 else 0

            if profit < 5 or roi < 0.015 or invest < 50:
                continue

            plan.append({
                'Ticker': row['Ticker'],
                'Buy': round(price, 2),
                'Sell': round(sell_price, 2),
                'Shares': max_shares,
                'Invest': round(invest, 2),
                'Profit': round(profit, 2),
                'AI Score': row['AI Recommendation (0–10)'],
                'Volatility %': row['Volatility (%)'],
                'Risk Score': round(row['Risk Score'], 2)
            })

            total_spent += invest
            total_profit += profit
            used_tickers.add(row['Ticker'])

            if total_profit >= target_profit and len(plan) >= 3:
                return plan, total_spent, total_profit

        st.info(f"🔄 Retry {attempt + 1}: Scanning more movers...")
        new_tickers = fetch_movers()
        new_candidates = []
        for ticker in new_tickers:
            if ticker not in full_pool['Ticker'].values:
                data = analyze_stock(ticker)
                if data:
                    new_candidates.append(data)
            if len(new_candidates) >= 15:
                break

        if not new_candidates:
            break

        df_new = pd.DataFrame(new_candidates)
        df_new['AI Recommendation (0–10)'] = 5
        df_new['Risk Score'] = df_new.apply(lambda r: (10 - 5) + r['Volatility (%)'] / 10, axis=1)
        full_pool = pd.concat([full_pool, df_new], ignore_index=True)

        attempt += 1
        time.sleep(1)

    return plan, total_spent, total_profit
