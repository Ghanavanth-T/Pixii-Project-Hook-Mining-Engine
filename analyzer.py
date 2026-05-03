import json
import time
from ai_client import get_ai_response

HOOK_ANALYSIS_PROMPT = """You are an expert content strategist analyzing viral social media posts.

Analyze these posts and extract DISTINCT hook patterns — the structural/psychological techniques used in opening lines to grab attention.

For each pattern provide:
- pattern_name: Specific, memorable name (NOT generic like "Question" or "Bold Claim" — be specific e.g. "The Exact Number Claim", "The Painful Mistake Confession")
- category: One of [curiosity_gap, social_proof, contrarian, storytelling, listicle, question, bold_claim, vulnerability, data_driven, humor, urgency, other]
- description: Why this pattern works psychologically (1-2 sentences)
- example: Best example from the posts below (copy the actual opening line)

Find 5-8 DISTINCT patterns. Be specific — avoid generic names. Only include patterns clearly visible in these posts.

POSTS:
{posts_text}

Return ONLY a valid JSON array. No markdown, no explanation."""

BATCH_SIZE = 20  # larger batches = more context = more varied patterns + fewer API calls


def _to_str(val) -> str:
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return str(val) if val is not None else ""


def _parse_json(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    if not text:
        return []
    patterns = json.loads(text)
    sanitized = []
    for p in patterns:
        if not isinstance(p, dict):
            continue
        sanitized.append({
            "pattern_name": _to_str(p.get("pattern_name", "")),
            "category":     _to_str(p.get("category", "other")),
            "description":  _to_str(p.get("description", "")),
            "example":      _to_str(p.get("example", "")),
        })
    return sanitized


def analyze_hooks(posts: list[dict]) -> list[dict]:
    if not posts:
        return []

    all_patterns = []
    total_batches = (len(posts) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(posts), BATCH_SIZE):
        batch = posts[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        posts_text = "\n\n---\n\n".join(
            f"[{p['source'].upper()} | Score:{p['score']}]\n"
            f"Title: {p.get('title', '').strip()}\n"
            f"Body: {p.get('body', '').strip()[:150]}"
            for p in batch
        )

        try:
            text = get_ai_response(HOOK_ANALYSIS_PROMPT.format(posts_text=posts_text), max_tokens=1500)
            patterns = _parse_json(text)
            if patterns:
                all_patterns.extend(patterns)
                print(f"  [Analyzer] Batch {batch_num}/{total_batches}: {len(patterns)} patterns")
        except json.JSONDecodeError:
            print(f"  [Analyzer] JSON error in batch {batch_num} — skipping")
        except Exception as e:
            print(f"  [Analyzer] Error in batch {batch_num}: {e}")

        if batch_num < total_batches:
            time.sleep(2)

    deduplicated = _deduplicate_patterns(all_patterns)
    print(f"[Analyzer] Final: {len(deduplicated)} unique patterns from {len(all_patterns)} raw")
    return deduplicated


def _deduplicate_patterns(patterns: list[dict]) -> list[dict]:
    """Deduplicate by normalized name, keep highest-quality example."""
    seen = {}
    for p in patterns:
        name = p.get("pattern_name", "").lower().strip()
        if not name:
            continue
        # Keep the one with the longer, more specific description
        if name not in seen or len(p.get("description", "")) > len(seen[name].get("description", "")):
            seen[name] = p

    unique = list(seen.values())
    # Sort by category diversity then cap at 40
    unique.sort(key=lambda x: x.get("category", ""))
    return unique[:40]


if __name__ == "__main__":
    sample = [
        {"source": "reddit", "score": 500, "title": "I made $10K in 30 days with this one strategy", "body": "Here's what I did..."},
        {"source": "reddit", "score": 800, "title": "Stop doing X. Start doing Y.", "body": "I've been in marketing for 10 years..."},
    ]
    results = analyze_hooks(sample)
    print(json.dumps(results, indent=2))
