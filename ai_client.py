"""
AI client — auto-detects which API key is set and uses that provider.
Priority: Groq → Gemini (fallback on rate limit)
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str, default: str = "") -> str:
    """Read from Streamlit secrets if available, else fall back to env vars."""
    try:
        import streamlit as st
        val = st.secrets.get(key, os.getenv(key, default))
        return val if val is not None else default
    except Exception:
        return os.getenv(key, default)


def get_ai_response(prompt: str, max_tokens: int = 2048) -> str:
    groq_key = _get_secret("GROQ_API_KEY")
    gemini_key = _get_secret("GEMINI_API_KEY")
    anthropic_key = _get_secret("ANTHROPIC_API_KEY")

    # Try Groq first
    if groq_key:
        try:
            return _call_groq(prompt, groq_key, max_tokens)
        except Exception as e:
            err = str(e).lower()
            if "rate_limit" in err or "429" in err or "quota" in err:
                print(f"  [AI] Groq rate limited — switching to Gemini")
                if gemini_key:
                    return _call_gemini(prompt, gemini_key, max_tokens)
                raise RuntimeError("Groq rate limited and no Gemini key available.")
            raise

    # Gemini only
    if gemini_key:
        return _call_gemini(prompt, gemini_key, max_tokens)

    # Anthropic fallback
    if anthropic_key:
        return _call_anthropic(prompt, anthropic_key, max_tokens)

    raise EnvironmentError(
        "No AI API key found. Set GROQ_API_KEY or GEMINI_API_KEY in your .env / Streamlit secrets."
    )


def _call_groq(prompt: str, api_key: str, max_tokens: int) -> str:
    from groq import Groq
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return response.choices[0].message.content


def _call_gemini(prompt: str, api_key: str, max_tokens: int) -> str:
    import requests as req

    GEMINI_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ]

    last_err = None
    for model in GEMINI_MODELS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
        }
        try:
            resp = req.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError(f"No candidates returned. Finish reason: {data}")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError(f"Empty content parts. Candidate: {candidates[0]}")

            text = parts[0].get("text", "").strip()
            if not text:
                raise ValueError(f"Empty text in response")

            return text

        except Exception as e:
            print(f"  [Gemini] {model} failed: {e}")
            last_err = e
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


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
