from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
from collector import run_all_collectors

def _run():
    asyncio.run(run_all_collectors())

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(_run, "interval", hours=6, id="scrape_and_predict")
    scheduler.start()
    print("[SCHEDULER] Auto-collection every 6 hours — started.")
