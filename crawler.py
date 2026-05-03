import time
import requests
import xml.etree.ElementTree as ET
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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def crawl_reddit_json(limit_per_sub: int = 100) -> list[dict]:
    """Crawl Reddit via public JSON API."""
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
            print(f"  [!] JSON error r/{sub_name}: {e}")
    return posts


def crawl_reddit_rss() -> list[dict]:
    """Crawl Reddit via RSS feeds — more reliable on cloud servers."""
    posts = []
    for i, sub_name in enumerate(VIRAL_SUBREDDITS):
        url = f"https://www.reddit.com/r/{sub_name}/hot.rss?limit=50"
        headers = {"User-Agent": USER_AGENTS[i % len(USER_AGENTS)]}
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)

            for j, entry in enumerate(entries):
                title = entry.findtext("atom:title", default="", namespaces=ns)
                content = entry.findtext("atom:content", default="", namespaces=ns) or ""
                link = entry.findtext("atom:link", default="", namespaces=ns)
                # RSS doesn't have scores, use position as proxy (top = more viral)
                score = max(50 - j * 2, VIRAL_THRESHOLD)
                posts.append({
                    "id": f"reddit_rss_{sub_name}_{j}",
                    "source": "reddit",
                    "subreddit_or_topic": sub_name,
                    "title": title,
                    "body": content[:3000],
                    "score": score,
                    "url": link,
                })
            time.sleep(1)
        except Exception as e:
            print(f"  [!] RSS error r/{sub_name}: {e}")
    return posts


def crawl_hackernews(pages: int = 3) -> list[dict]:
    """
    Crawl HackerNews top stories — 100% free, no auth needed.
    Great source of startup, ecommerce, and marketing hooks.
    """
    posts = []
    try:
        # Get top story IDs
        resp = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        story_ids = resp.json()[:pages * 30]

        for story_id in story_ids:
            try:
                story_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=10
                )
                story = story_resp.json()
                if not story or story.get("type") != "story":
                    continue
                score = story.get("score", 0)
                if score < 50:
                    continue
                posts.append({
                    "id": f"hn_{story_id}",
                    "source": "hackernews",
                    "subreddit_or_topic": "hackernews",
                    "title": story.get("title", ""),
                    "body": story.get("text", "") or "",
                    "score": score,
                    "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                })
                time.sleep(0.1)
            except Exception:
                continue

    except Exception as e:
        print(f"  [!] HackerNews error: {e}")

    print(f"  [HackerNews] Crawled {len(posts)} posts")
    return posts


def crawl_reddit(limit_per_sub: int = 50) -> list[dict]:
    """Try JSON first, fall back to RSS if blocked."""
    posts = crawl_reddit_json(limit_per_sub)
    if len(posts) == 0:
        print("  [Reddit] JSON blocked — trying RSS fallback...")
        posts = crawl_reddit_rss()
    print(f"  [Reddit] Crawled {len(posts)} posts from {len(VIRAL_SUBREDDITS)} subreddits")
    return posts


def crawl_all() -> list[dict]:
    print("[Crawler] Starting crawl...")
    posts = []
    posts.extend(crawl_reddit())
    posts.extend(crawl_hackernews())
    posts.sort(key=lambda p: p.get("score", 0), reverse=True)
    print(f"[Crawler] Total: {len(posts)} posts collected")
    return posts


if __name__ == "__main__":
    results = crawl_all()
    print(f"Crawled {len(results)} posts")
    for p in results[:5]:
        print(f"  [{p['source']}] score={p['score']} | {p['title'][:60] or p['body'][:60]}")
