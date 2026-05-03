import json
import time
from dotenv import load_dotenv
from ai_client import get_ai_response, _get_secret
from database import get_top_patterns, save_generated_post

load_dotenv()

DEFAULT_BRAND_VOICE = (
    "Pixii is an AI designer for Amazon listings. It creates beautiful, editable listing designs "
    "with zero prompts — scaling 1 listing to 1,000 products in 2 minutes, vs $5,000 and 9 weeks "
    "with an agency. Proven to grow Amazon revenue 30-300%. Founded as a Bain & Company spin-out; "
    "customers doing $10B+ revenue. Vision: Visuals that sell, everywhere you sell. "
    "Voice: confident, ROI-focused, direct. Audience: Amazon sellers, DTC brands, e-commerce operators."
)

GENERATION_PROMPT = """Write {count} social media posts for Pixii, an AI tool that designs Amazon listings.

Platform: {platform}
Brand: {brand_voice}

Use these hook patterns as your opening structure:
{patterns_summary}

Rules:
- Each post must open with one of the hook patterns above
- Include real numbers: 2 minutes, 30-300% revenue growth, $5000 agency cost, 1000 listings
- {platform_rule}
- Ready to post, no placeholders
- Add relevant emojis naturally

Return a JSON array with fields: "hook_pattern_used", "content", "platform"
Return ONLY valid JSON. No markdown fences."""

PLATFORM_RULES = {
    "twitter": "Max 280 characters",
    "linkedin": "Max 500 characters, professional tone",
    "instagram": "Max 400 characters, include hashtags",
}


def generate_posts(count: int = 5, platform: str = "twitter") -> list[dict]:
    brand_voice = _get_secret("PIXII_BRAND_VOICE", DEFAULT_BRAND_VOICE)
    patterns = get_top_patterns(limit=10)

    if not patterns:
        raise ValueError("No hook patterns in library yet. Run the full pipeline first.")

    # Only use names + descriptions (no raw examples) to avoid safety filter triggers
    patterns_summary = "\n".join(
        f"- {p['pattern_name']} ({p['category']}): {p['description']}"
        for p in patterns[:8]
    )

    platform_rule = PLATFORM_RULES.get(platform, "Keep it concise")

    # Wait for rate limits to clear after analysis
    time.sleep(5)

    text = get_ai_response(
        GENERATION_PROMPT.format(
            count=count,
            platform=platform,
            brand_voice=brand_voice,
            patterns_summary=patterns_summary,
            platform_rule=platform_rule,
        ),
        max_tokens=2000,
    )

    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    if not text:
        raise ValueError("AI returned empty response during generation.")

    generated = json.loads(text)
    if not isinstance(generated, list):
        generated = [generated]

    pattern_id_map = {p["pattern_name"]: p["id"] for p in patterns}
    saved = 0
    for post in generated:
        content = str(post.get("content", "")).strip()
        if not content:
            continue
        pid = pattern_id_map.get(post.get("hook_pattern_used"), 0)
        save_generated_post(content, pid, platform)
        saved += 1

    print(f"[Generator] Saved {saved} posts for {platform}")
    return generated


if __name__ == "__main__":
    posts = generate_posts(count=5, platform="twitter")
    for p in posts:
        print(f"\n[{p.get('hook_pattern_used', '?')}]")
        print(p["content"])
