"""
AI client — auto-detects which API key is set and uses that provider.
Priority: Groq → Gemini → Anthropic
Reads from Streamlit secrets (cloud) or .env (local) automatically.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str, default: str = "") -> str:
    """Read from Streamlit secrets if available, else fall back to env vars."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)


def get_ai_response(prompt: str, max_tokens: int = 4096) -> str:
    groq_key = _get_secret("GROQ_API_KEY")
    gemini_key = _get_secret("GEMINI_API_KEY")
    anthropic_key = _get_secret("ANTHROPIC_API_KEY")

    # Try Groq first, fall back to Gemini on rate limit
    if groq_key:
        try:
            return _call_groq(prompt, groq_key, max_tokens)
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                print(f"  [AI] Groq rate limited — falling back to Gemini")
                if gemini_key:
                    return _call_gemini(prompt, gemini_key, max_tokens)
            raise

    if gemini_key:
        return _call_gemini(prompt, gemini_key, max_tokens)

    if anthropic_key:
        return _call_anthropic(prompt, anthropic_key, max_tokens)

    raise EnvironmentError(
        "No AI API key found. Set GROQ_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY."
    )


def _call_groq(prompt: str, api_key: str, max_tokens: int) -> str:
    from groq import Groq
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # 20,000 TPM on free tier — highest available
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def _call_gemini(prompt: str, api_key: str, max_tokens: int) -> str:
    import requests as req
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens}
    }
    resp = req.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_anthropic(prompt: str, api_key: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def active_provider() -> str:
    if _get_secret("GROQ_API_KEY"):
        return "Groq"
    elif _get_secret("GEMINI_API_KEY"):
        return "Gemini"
    elif _get_secret("ANTHROPIC_API_KEY"):
        return "Anthropic"
    return "None"
