import os
import json
import anthropic
from dotenv import load_dotenv
from database import get_top_patterns, save_generated_post

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DEFAULT_BRAND_VOICE = (
    "Pixii is a bold, Gen-Z energy drink brand. Voice: witty, punchy, irreverent, meme-aware. "
    "Target: 18-28 year olds who love gaming, fitness, and hustle culture."
)

GENERATION_PROMPT = """You are a viral social media copywriter for the brand Pixii.

Brand voice: {brand_voice}

Using the following proven hook patterns from our Hook Library, write {count} social media posts for Pixii. Each post should:
1. Use one of the hook patterns as its opening structure
2. Be tailored for {platform}
3. Stay true to the Pixii brand voice
4. Be ready to post (no placeholders)
5. Include relevant emojis where natural
6. Be under 280 characters for Twitter, under 500 for LinkedIn/Instagram

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
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": GENERATION_PROMPT.format(
                    brand_voice=brand_voice,
                    count=count,
                    platform=platform,
                    patterns_json=json.dumps(patterns_for_prompt, indent=2),
                )
            }],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

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
