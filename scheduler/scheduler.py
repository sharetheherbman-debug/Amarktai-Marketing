"""AMarkTAI Autonomous Campaign Scheduler"""
import os, logging
from apscheduler.schedulers.blocking import BlockingScheduler
from pymongo import MongoClient
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://amarktai:amarktai_db_pass@mongodb:27017/amarktai_mkt")
SCRAPER_URL = os.getenv("SCRAPER_API_URL", "http://scraper:3000")
AUTH_URL = os.getenv("AUTH_API_URL", "http://auth:8085")

mongo = MongoClient(MONGODB_URL)
db = mongo["amarktai_mkt"]
schedules_col = db["schedules"]

scheduler = BlockingScheduler()

async def run_scheduled_campaign(schedule_doc):
    """Execute a scheduled campaign"""
    user_id = schedule_doc["user_id"]
    url = schedule_doc["url"]
    logger.info(f"Running scheduled campaign for user {user_id}: {url}")
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            # Check quota
            resp = await client.post(f"{AUTH_URL}/auth/check-quota",
                headers={"Authorization": f"Bearer {schedule_doc.get('token', '')}"})
            if resp.status_code != 200:
                logger.warning(f"Quota exceeded for user {user_id}")
                return
            # Trigger scraper
            scrape_resp = await client.post(f"{SCRAPER_URL}/scrape", json={"url": url})
            if scrape_resp.status_code == 200:
                logger.info(f"Scrape successful for {url}, content ready for generation")
                # TODO: Wire to GenX generation pipeline via Router API
            else:
                logger.error(f"Scrape failed: {scrape_resp.text}")
    except Exception as e:
        logger.error(f"Campaign error: {e}")

def check_schedules():
    """Check MongoDB for pending scheduled campaigns"""
    from datetime import datetime
    now = datetime.utcnow()
    pending = schedules_col.find({"next_run": {"$lte": now}, "active": True})
    for doc in pending:
        import asyncio
        asyncio.run(run_scheduled_campaign(doc))
        # Update next_run based on frequency
        schedules_col.update_one({"_id": doc["_id"]}, {"$set": {"last_run": now}})
    logger.info(f"Schedule check complete. Active schedules: {schedules_col.count_documents({'active': True})}")

# Run every 15 minutes
scheduler.add_job(check_schedules, 'interval', minutes=15, id='check_schedules')

if __name__ == "__main__":
    logger.info("AMarkTAI Scheduler started")
    scheduler.start()
