from dotenv import load_dotenv
import os

load_dotenv()

print("USE_OPENAI =", os.getenv("USE_OPENAI"))
print("OPENAI_API_KEY =", os.getenv("OPENAI_API_KEY"))

from utils.openai_helper import generate_ai_score

sample_row = {
    'Ticker': 'AAPL',
    'Company Name': 'Apple Inc.',
    'Sector': 'Technology',
    'Volume': 5000000,
    'Change (%)': 2.5,
    'Volatility (%)': 4.2
}

response, score = generate_ai_score(sample_row)

print("AI Response:\n", response)
print("AI Score:", score)
