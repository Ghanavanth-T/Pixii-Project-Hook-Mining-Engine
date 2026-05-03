import json
import time
from ai_client import get_ai_response

HOOK_ANALYSIS_PROMPT = """You are an expert content strategist who studies viral hooks — the opening lines or structures that make social media posts go viral.

Analyze the following batch of viral posts and extract the HOOK PATTERNS you see. A hook pattern is a repeatable structural or psychological technique used in the opening of a post to grab attention.

For each pattern you find, provide:
- pattern_name: A short, memorable name (e.g., "Controversial Hot Take", "Before/After Transformation")
- category: One of [curiosity_gap, social_proof, contrarian, storytelling, listicle, question, bold_claim, vulnerability, data_driven, humor, urgency, other]
- description: 1-2 sentences explaining the pattern and why it works
- example: A cleaned-up example from the posts (or a synthesized one)

Return a JSON array of 3-5 patterns maximum. Only include genuinely distinct patterns you see in these posts.

VIRAL POSTS:
{posts_text}

Return ONLY valid JSON — no markdown fences, no explanation. Just the array."""

BATCH_SIZE = 7  # small batches to stay within Groq free tier token limits


def _parse_json(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    patterns = json.loads(text)
    # Sanitize — force all fields to strings so SQLite never gets a dict/list
    sanitized = []
    for p in patterns:
        sanitized.append({
            "pattern_name": _to_str(p.get("pattern_name", "")),
            "category":     _to_str(p.get("category", "other")),
            "description":  _to_str(p.get("description", "")),
            "example":      _to_str(p.get("example", "")),
        })
    return sanitized


def _to_str(val) -> str:
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return str(val) if val is not None else ""


def analyze_hooks(posts: list[dict]) -> list[dict]:
    if not posts:
        return []

    all_patterns = []

    for i in range(0, len(posts), BATCH_SIZE):
        batch = posts[i:i + BATCH_SIZE]
        posts_text = "\n\n---\n\n".join(
            f"[Source: {p['source']} | Score: {p['score']}]\n"
            f"Title: {p.get('title', 'N/A')}\n"
            f"Body: {p.get('body', '')[:200]}"
            for p in batch
        )

        try:
            text = get_ai_response(HOOK_ANALYSIS_PROMPT.format(posts_text=posts_text))
            patterns = _parse_json(text)
            all_patterns.extend(patterns)
            print(f"  [Analyzer] Batch {i // BATCH_SIZE + 1}: found {len(patterns)} patterns")
        except json.JSONDecodeError as e:
            print(f"  [Analyzer] JSON parse error in batch {i // BATCH_SIZE + 1}: {e}")
        except Exception as e:
            print(f"  [Analyzer] Error in batch {i // BATCH_SIZE + 1}: {e}")

        time.sleep(3)  # wait between batches to respect Groq rate limits

    deduplicated = _deduplicate_patterns(all_patterns)
    print(f"[Analyzer] Total unique patterns: {len(deduplicated)}")
    return deduplicated


def _deduplicate_patterns(patterns: list[dict]) -> list[dict]:
    """Deduplicate by name first (fast), then cap at 30 meaningful patterns."""
    seen = {}
    for p in patterns:
        name = p.get("pattern_name", "").lower().strip()
        if name and name not in seen:
            seen[name] = p

    unique = list(seen.values())

    # Hard cap — hooks are not infinite, 30 is more than enough
    return unique[:30]


if __name__ == "__main__":
    sample = [
        {"source": "reddit", "score": 500, "title": "I made $10K in 30 days with this one strategy", "body": "Here's what I did..."},
        {"source": "reddit", "score": 800, "title": "Stop doing X. Start doing Y.", "body": "I've been in marketing for 10 years..."},
    ]
    results = analyze_hooks(sample)
    print(json.dumps(results, indent=2))
