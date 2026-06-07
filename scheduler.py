"""
scheduler.py — Auto-runs data collection on a schedule
Add this to your lifespan context in main.py for automatic updates.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from collector import run_all_collectors

scheduler = AsyncIOScheduler()

def start_scheduler():
    # Collect data every 6 hours automatically
    scheduler.add_job(
        run_all_collectors,
        trigger="interval",
        hours=6,
        id="collect_sports_data",
        replace_existing=True,
    )
    scheduler.start()
    print("[SCHEDULER] Auto-collection every 6 hours — started.")

def stop_scheduler():
    scheduler.shutdown()
    print("[SCHEDULER] Stopped.")
