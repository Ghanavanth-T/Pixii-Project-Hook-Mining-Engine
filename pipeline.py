"""
Hook Mining Engine — Main Pipeline
Runs the full crawl → analyze → generate cycle.
Can be triggered manually or scheduled via APScheduler.
"""

import sys
from datetime import datetime
from crawler import crawl_all
from analyzer import analyze_hooks
from generator import generate_posts
from database import save_viral_posts, save_hook_patterns, start_pipeline_run, finish_pipeline_run


def run_pipeline(generate_count: int = 5):
    print(f"\n{'='*60}")
    print(f"  HOOK MINING ENGINE — Pipeline Run")
    print(f"  Started: {datetime.utcnow().isoformat()}")
    print(f"{'='*60}\n")

    run_id = start_pipeline_run()

    try:
        # Step 1: Crawl viral posts
        print("[Step 1/3] Crawling viral posts...")
        posts = crawl_all()
        saved_count = save_viral_posts(posts)
        print(f"  Saved {saved_count} new posts to database\n")

        # Step 2: Analyze hooks with Claude
        print("[Step 2/3] Analyzing hook patterns with Claude...")
        patterns = analyze_hooks(posts)
        post_ids = [p["id"] for p in posts[:30]]
        new_patterns = save_hook_patterns(patterns, post_ids)
        print(f"  {new_patterns} new patterns added, {len(patterns) - new_patterns} existing updated\n")

        # Step 3: Generate Pixii posts
        print("[Step 3/3] Generating Pixii posts...")
        generated = generate_posts(count=generate_count, platform="twitter")
        generated += generate_posts(count=generate_count, platform="linkedin")
        print(f"  Generated {len(generated)} total posts\n")

        finish_pipeline_run(run_id, saved_count, len(patterns), len(generated))

        print(f"{'='*60}")
        print(f"  Pipeline complete!")
        print(f"  Posts crawled: {saved_count}")
        print(f"  Patterns found: {len(patterns)}")
        print(f"  Posts generated: {len(generated)}")
        print(f"{'='*60}\n")

        return {"crawled": saved_count, "patterns": len(patterns), "generated": len(generated)}

    except Exception as e:
        finish_pipeline_run(run_id, 0, 0, 0, status=f"error: {e}")
        print(f"\n[!] Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_pipeline(generate_count=count)
