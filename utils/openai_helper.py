# utils/openai_helper.py
import os
import requests

def call_openai_chat(prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""  # No key provided

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
    except requests.exceptions.HTTPError as e:
        return ""  # Optionally log e.response.text or e.status_code
    except Exception:
        return ""  # Fail silently
