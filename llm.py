"""Shared, optional LLM access (OpenAI or Groq via the OpenAI-compatible API).

Everything in the app works without a key; LLM calls only add narrative on top.
"""
import os


def provider():
    """Pick a provider from .env: OpenAI first, then Groq (free tier)."""
    if os.getenv("OPENAI_API_KEY") and "your-key" not in os.getenv("OPENAI_API_KEY", ""):
        return {"api_key": os.getenv("OPENAI_API_KEY"), "base_url": None,
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "name": "OpenAI"}
    if os.getenv("GROQ_API_KEY") and "your_groq" not in os.getenv("GROQ_API_KEY", ""):
        return {"api_key": os.getenv("GROQ_API_KEY"), "base_url": "https://api.groq.com/openai/v1",
                "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"), "name": "Groq"}
    return None


def chat(system, user, temperature=0.2):
    """Return the model's reply, None when no key is configured, or a short error note."""
    p = provider()
    if not p:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=p["api_key"], base_url=p["base_url"])
        resp = client.chat.completions.create(
            model=p["model"], temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content
    except Exception as e:  # never break the app because of the LLM
        return f"_AI answer unavailable ({type(e).__name__}). Check the API key in .env._"
