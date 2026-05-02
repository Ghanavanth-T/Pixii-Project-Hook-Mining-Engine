import os
import json
from dotenv import load_dotenv
from ai_client import get_ai_response
from database import get_top_patterns, save_generated_post

load_dotenv()

DEFAULT_BRAND_VOICE = (
    "Pixii is an AI designer for Amazon listings. It creates beautiful, editable listing designs "
    "with zero prompts — scaling 1 listing to 1,000 products in 2 minutes, vs $5,000 and 9 weeks "
    "with an agency. Proven to grow Amazon revenue 30-300%. Founded as a Bain & Company spin-out; "
    "customers doing $10B+ revenue. Vision: 'Visuals that sell, everywhere you sell.' "
    "Voice: confident, ROI-obsessed, founder-credible. Audience: Amazon sellers, DTC brands, "
    "e-commerce operators. Lead with speed, scale, and revenue impact."
)

GENERATION_PROMPT = """You are a viral social media copywriter for Pixii.

Brand context: {brand_voice}

Using the following proven hook patterns from our Hook Library, write {count} social media posts for Pixii. Each post should:
1. Use one of the hook patterns as its opening structure
2. Be tailored for {platform} (Amazon sellers, DTC brand owners, e-commerce operators)
3. Lead with a specific, concrete benefit — speed, cost savings, revenue growth, or scale
4. Reference real numbers when possible (2 minutes, $5,000 agency cost, 30-300% revenue growth, 1,000 listings)
5. Be ready to post with no placeholders
6. Include relevant emojis where natural
7. Be under 280 characters for Twitter, under 500 for LinkedIn/Instagram

Hook Patterns to use:
{patterns_json}

Return a JSON array of objects with fields:
- "hook_pattern_used": name of the pattern
- "content": the full post text
- "platform": "{platform}"

Return ONLY valid JSON — no markdown fences."""


def generate_posts(count: int = 5, platform: str = "twitter") -> list[dict]:
    brand_voice = os.getenv("PIXII_BRAND_VOICE", DEFAULT_BRAND_VOICE)
    patterns = get_top_patterns(limit=10)

    if not patterns:
        print("[Generator] No hook patterns in library yet. Run the pipeline first.")
        return []

    patterns_for_prompt = [
        {"pattern_name": p["pattern_name"], "category": p["category"],
         "description": p["description"], "example": p["example"]}
        for p in patterns
    ]

    try:
        text = get_ai_response(GENERATION_PROMPT.format(
            brand_voice=brand_voice,
            count=count,
            platform=platform,
            patterns_json=json.dumps(patterns_for_prompt, indent=2),
        ))

        if text.strip().startswith("```"):
            text = text.strip().split("\n", 1)[1].rsplit("```", 1)[0].strip()

        generated = json.loads(text)
        pattern_id_map = {p["pattern_name"]: p["id"] for p in patterns}
        for post in generated:
            pid = pattern_id_map.get(post.get("hook_pattern_used"), None)
            save_generated_post(post["content"], pid or 0, platform)

        print(f"[Generator] Created {len(generated)} posts for {platform}")
        return generated

    except Exception as e:
        print(f"[Generator] Error: {e}")
        return []


if __name__ == "__main__":
    posts = generate_posts(count=5, platform="twitter")
    for p in posts:
        print(f"\n[{p.get('hook_pattern_used', '?')}]")
        print(p["content"])
