import os
import time
import requests
from dotenv import load_dotenv
from ai_client import _get_secret

load_dotenv()

VIRAL_SUBREDDITS = [
    # Amazon & e-commerce sellers (primary audience)
    "FulfillmentByAmazon", "AmazonSeller", "ecommerce", "amazonsellers",
    # DTC / brand building
    "Entrepreneur", "startups", "shopify",
    # Copywriting & conversion (hook patterns)
    "copywriting", "marketing", "growmybusiness",
    # Product listing / design
    "ProductDesign", "branding",
]

VIRAL_THRESHOLD = 10

# Rotate user agents to avoid blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def crawl_reddit_direct(limit_per_sub: int = 100) -> list[dict]:
    """Crawl Reddit using public JSON API — works locally, may be blocked on cloud."""
    import random
    posts = []

    for i, sub_name in enumerate(VIRAL_SUBREDDITS):
        url = f"https://www.reddit.com/r/{sub_name}/hot.json?limit={limit_per_sub}"
        headers = {"User-Agent": USER_AGENTS[i % len(USER_AGENTS)]}
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                score = post.get("score", 0)
                if score < VIRAL_THRESHOLD:
                    continue
                posts.append({
                    "id": f"reddit_{post['id']}",
                    "source": "reddit",
                    "subreddit_or_topic": sub_name,
                    "title": post.get("title", ""),
                    "body": (post.get("selftext", "") or "")[:3000],
                    "score": score,
                    "url": f"https://reddit.com{post.get('permalink', '')}",
                })

            time.sleep(1)

        except Exception as e:
            print(f"  [!] Error crawling r/{sub_name}: {e}")

    return posts


def crawl_reddit_apify(token: str) -> list[dict]:
    """Crawl Reddit via Apify — works on cloud, bypasses IP blocks."""
    posts = []

    for sub_name in VIRAL_SUBREDDITS[:6]:  # limit to avoid long timeouts
        run_url = "https://api.apify.com/v2/acts/trudax~reddit-scraper-lite/run-sync-get-dataset-items"
        payload = {
            "startUrls": [{"url": f"https://www.reddit.com/r/{sub_name}/hot/"}],
            "maxItems": 50,
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            resp = requests.post(run_url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            items = resp.json()

            for item in items:
                score = item.get("upVotes", item.get("score", 0))
                if score < VIRAL_THRESHOLD:
                    continue
                posts.append({
                    "id": f"reddit_{item.get('id', item.get('url', '')[-10:])}",
                    "source": "reddit",
                    "subreddit_or_topic": sub_name,
                    "title": item.get("title", ""),
                    "body": (item.get("body", item.get("text", "")) or "")[:3000],
                    "score": score,
                    "url": item.get("url", ""),
                })

        except Exception as e:
            print(f"  [!] Apify Reddit error for r/{sub_name}: {e}")

    return posts


def crawl_reddit(limit_per_sub: int = 100) -> list[dict]:
    """Try direct Reddit first, fall back to Apify if blocked."""
    token = _get_secret("APIFY_API_TOKEN")

    # Try direct first
    posts = crawl_reddit_direct(limit_per_sub)

    if len(posts) == 0 and token:
        print("  [Reddit] Direct crawl returned 0 posts — trying Apify fallback...")
        posts = crawl_reddit_apify(token)

    print(f"  [Reddit] Crawled {len(posts)} viral posts from {len(VIRAL_SUBREDDITS)} subreddits")
    return posts


def crawl_twitter_apify(query: str = "Amazon listing OR Amazon seller OR ecommerce growth OR product listing design", max_tweets: int = 200) -> list[dict]:
    token = _get_secret("APIFY_API_TOKEN")
    if not token:
        print("  [Twitter/X] Skipped — no APIFY_API_TOKEN set")
        return []

    run_url = "https://api.apify.com/v2/acts/quacker~twitter-scraper/run-sync-get-dataset-items"
    payload = {
        "searchTerms": [query],
        "maxTweets": max_tweets,
        "sort": "Top",
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        resp = requests.post(run_url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        tweets = resp.json()
    except Exception as e:
        print(f"  [Twitter/X] Apify error: {e}")
        return []

    posts = []
    for t in tweets:
        if t.get("likeCount", 0) < 50:
            continue
        posts.append({
            "id": f"twitter_{t.get('id', '')}",
            "source": "twitter",
            "subreddit_or_topic": "twitter_search",
            "title": "",
            "body": t.get("full_text", t.get("text", ""))[:3000],
            "score": t.get("likeCount", 0) + t.get("retweetCount", 0),
            "url": t.get("url", ""),
        })

    print(f"  [Twitter/X] Crawled {len(posts)} viral tweets via Apify")
    return posts


def crawl_all() -> list[dict]:
    print("[Crawler] Starting crawl...")
    posts = []
    posts.extend(crawl_reddit())
    posts.extend(crawl_twitter_apify())
    posts.sort(key=lambda p: p.get("score", 0), reverse=True)
    print(f"[Crawler] Total: {len(posts)} viral posts collected")
    return posts


if __name__ == "__main__":
    results = crawl_all()
    print(f"Crawled {len(results)} posts")
    for p in results[:5]:
        print(f"  [{p['source']}] score={p['score']} | {p['title'][:60] or p['body'][:60]}")
