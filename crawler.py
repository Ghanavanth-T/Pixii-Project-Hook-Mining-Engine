import os
import time
import requests
from dotenv import load_dotenv

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
HEADERS = {"User-Agent": "HookMiningEngine/1.0 (hook pattern research)"}


def crawl_reddit(limit_per_sub: int = 100) -> list[dict]:
    posts = []

    for sub_name in VIRAL_SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub_name}/hot.json?limit={limit_per_sub}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
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

            time.sleep(1)  # respect rate limits

        except Exception as e:
            print(f"  [!] Error crawling r/{sub_name}: {e}")

    print(f"  [Reddit] Crawled {len(posts)} viral posts from {len(VIRAL_SUBREDDITS)} subreddits")
    return posts


def crawl_twitter_apify(query: str = "Amazon listing OR Amazon seller OR ecommerce growth OR product listing design", max_tweets: int = 200) -> list[dict]:
    token = os.getenv("APIFY_API_TOKEN")
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
