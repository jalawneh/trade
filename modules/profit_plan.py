import streamlit as st
import pandas as pd
import yfinance as yf
from modules.stock_dashboard import display_stock_dashboard
from utils.openai_helper import get_final_score_justification
import os

USE_OPENAI = os.getenv("USE_OPENAI", "False").lower() == "true"

def show_profit_plan():
    st.title("\U0001F4B0 Smart Profit Plan")

    if 'allocated_stocks' not in st.session_state:
        st.warning("⚠️ Please run the Risk Allocation module first.")
        return

    st.markdown("### \U0001F4C8 Plan Configuration")
    budget = st.number_input("Enter your total investment budget ($):", min_value=100, value=3000)
    profit_goal = st.number_input("Enter your desired profit goal ($):", min_value=10, value=100)

    # Fetch allocation percentages
    risk_allocations = {
        "Low": st.session_state.low_risk,
        "Medium": st.session_state.med_risk,
        "High": st.session_state.high_risk
    }

    plan, total_spent, total_profit = simulate_plan(
        df=st.session_state['allocated_stocks'],
        budget=budget,
        allocations=risk_allocations
    )

    if plan:
        st.subheader("\U0001F4CA Profit Plan")
        st.write(f"Total Investment: ${total_spent:.2f}")
        st.write(f"Expected Profit: ${total_profit:.2f} (Goal: ${profit_goal:.2f})")
        plan_df = pd.DataFrame(plan)
        st.dataframe(plan_df)

        for row in plan:
            display_stock_dashboard(row['Ticker'])
            if USE_OPENAI:
                st.markdown("### 🧠 AI Score Justification")
                justification = get_final_score_justification(str(row))
                st.info(justification)

    else:
        st.warning("No suitable stocks met the profit criteria for your budget.")

def simulate_plan(df, budget, allocations):
    plan = []
    total_spent = total_profit = 0

    for tier in ["Low", "Medium", "High"]:
        tier_df = df[df['Risk Tier'] == tier]
        tier_budget = budget * (allocations[tier] / 100)

        if tier_df.empty or tier_budget < 1:
            continue

        sorted_tier = tier_df.sort_values(by=["Score"], ascending=False).reset_index(drop=True)

        for _, row in sorted_tier.iterrows():
            price = row.get("Last Close ($)", 0)
            if price == 0:
                continue

            stock = yf.Ticker(row['Ticker'])
            hist = stock.history(period="2d", interval="1h")
            peak_48h = hist['High'].max() if not hist.empty else price

            volatility = max(3, row['Volatility (%)']) / 2
            est_price = price * (1 + volatility / 100)
            sell_price = max(est_price, peak_48h)

            max_shares = int(tier_budget / price)
            if max_shares <= 0:
                continue

            invest = max_shares * price
            profit = (sell_price - price) * max_shares
            roi = profit / invest if invest > 0 else 0
            potential_roi = (profit / budget) * 100

            if profit < 5 or roi < 0.015 or invest < 50:
                continue

            plan.append({
                'Ticker': row['Ticker'],
                'Buy': round(price, 2),
                'Sell': round(sell_price, 2),
                'Shares': max_shares,
                'Invest': round(invest, 2),
                'Profit': round(profit, 2),
                'ROI % of Budget': round(potential_roi, 2),
                'AI Score': row['AI Recommendation (0-10)'],
                'Volatility %': row['Volatility (%)'],
                'Risk Tier': tier
            })

            total_spent += invest
            total_profit += profit

            tier_budget -= invest
            if tier_budget < price:
                break

    return plan, total_spent, total_profit
