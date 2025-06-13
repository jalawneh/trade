# modules/profit_plan.py
import streamlit as st
import pandas as pd
import yfinance as yf
from modules.stock_dashboard import display_stock_dashboard


def show_profit_plan():
    st.title("\U0001F4B0 Smart Profit Plan")

    if 'top10' not in st.session_state:
        st.warning("⚠️ Please run the Market Scan first to generate stock data.")
        return

    def get_ranked_candidates():
        top = st.session_state['top10']
        top['Risk Score'] = top.apply(lambda r: (10 - r['AI Recommendation (0–10)']) + r['Volatility (%)'] / 10, axis=1)
        return top.sort_values(by=['Risk Score', 'AI Recommendation (0–10)'], ascending=[True, False]).copy()

    candidates = get_ranked_candidates()
    plan, total_spent, total_profit = simulate_plan(candidates)

    if plan:
        st.subheader("\U0001F4CA Profit Plan")
        st.write(f"Total Investment: ${total_spent:.2f}")
        st.write(f"Expected Profit: ${total_profit:.2f}")
        plan_df = pd.DataFrame(plan)
        st.dataframe(plan_df)

        for row in plan:
            display_stock_dashboard(row['Ticker'])

    else:
        st.warning("Unable to generate a profit plan with the current data.")


def simulate_plan(candidates, budget=3000):
    plan = []
    total_spent = total_profit = 0
    used_tickers = set()

    grouped = candidates.groupby("Risk Score")
    max_allocation_per_stock = budget * 0.33

    for risk_score, group in grouped:
        group_sorted = group.sort_values(by="Score", ascending=False).reset_index(drop=True)
        normalized_weights = [(1 / (1 + row['Risk Score'])) for _, row in group_sorted.iterrows()]
        weight_sum = sum(normalized_weights)

        for i, (_, row) in enumerate(group_sorted.iterrows()):
            if row['Ticker'] in used_tickers:
                continue

            share_weight = normalized_weights[i] / weight_sum
            allocation = min(budget * share_weight, max_allocation_per_stock)
            if len(group_sorted) > 1 and allocation > budget * 0.15:
                allocation = budget * 0.15

            remaining_budget = budget - total_spent
            allocation = min(allocation, remaining_budget)

            price = row['Last Close ($)']
            ticker = row['Ticker']
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d", interval="1h")
            peak_48h = hist['High'].max() if not hist.empty else price

            volatility = max(3, row['Volatility (%)']) / 2
            est_price = price * (1 + volatility / 100)
            sell_price = max(est_price, peak_48h)

            max_shares = int(allocation / price)

            if max_shares <= 0:
                st.info(f"⛔ Skipping {row['Ticker']} - not enough budget for even one share.")
                continue

            invest = max_shares * price
            profit = (sell_price - price) * max_shares
            roi = profit / invest if invest > 0 else 0
            potential_roi = (profit / budget) * 100

            if profit < 5 or roi < 0.015 or invest < 50:
                st.info(f"❌ {row['Ticker']} filtered out - Profit: ${profit:.2f}, ROI: {roi:.2f}, Invest: ${invest:.2f}")
                continue

            st.success(f"✅ Added {row['Ticker']} - Profit: ${profit:.2f}, ROI: {roi:.2f}")

            plan.append({
                'Ticker': row['Ticker'],
                'Buy': round(price, 2),
                'Sell': round(sell_price, 2),
                'Shares': max_shares,
                'Invest': round(invest, 2),
                'Profit': round(profit, 2),
                'ROI % of Budget': round(potential_roi, 2),
                'AI Score': row['AI Recommendation (0–10)'],
                'Volatility %': row['Volatility (%)'],
                'Risk Score': round(row['Risk Score'], 2)
            })

            total_spent += invest
            total_profit += profit
            used_tickers.add(row['Ticker'])

    return plan, total_spent, total_profit
