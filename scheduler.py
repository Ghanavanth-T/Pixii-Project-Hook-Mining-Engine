"""
Scheduler — runs the Hook Mining pipeline automatically on a weekly schedule.
This makes the engine "run on its own" as required.
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from pipeline import run_pipeline

scheduler = BlockingScheduler()


@scheduler.scheduled_job("cron", day_of_week="mon", hour=6, minute=0, id="weekly_hook_mining")
def weekly_run():
    print("\n[Scheduler] Weekly hook mining triggered")
    run_pipeline(generate_count=5)


@scheduler.scheduled_job("cron", day_of_week="thu", hour=12, minute=0, id="midweek_generation")
def midweek_generation():
    from generator import generate_posts
    print("\n[Scheduler] Midweek post generation triggered")
    generate_posts(count=5, platform="twitter")
    generate_posts(count=3, platform="linkedin")


if __name__ == "__main__":
    print("[Scheduler] Hook Mining Engine scheduler started")
    print("  - Full pipeline: Every Monday at 6:00 AM UTC")
    print("  - Extra generation: Every Thursday at 12:00 PM UTC")
    print("  Press Ctrl+C to stop\n")
    scheduler.start()
