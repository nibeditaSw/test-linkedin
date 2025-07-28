# app/scheduler_worker.py
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from app.database import SessionLocal, ScheduledPost
from app.linkedin import get_linkedin_user_id, post_to_linkedin
from dotenv import load_dotenv
import os


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")

def scheduled_job(post_id, text, image_url):
    logger.debug(f"Scheduler triggered for post {post_id}")
    access_token = LINKEDIN_ACCESS_TOKEN
    if not access_token:
        logger.error("LINKEDIN_ACCESS_TOKEN is not set")
        return
    user_id = get_linkedin_user_id(access_token)
    if not user_id:
        logger.error("Cannot get LinkedIn user ID")
        return
    success = post_to_linkedin(text, access_token, user_id, image_url)
    db = SessionLocal()
    post = db.query(ScheduledPost).filter_by(post_id=post_id).first()
    if post and success:
        post.posted = True
        db.commit()
        logger.info(f"Post {post_id} marked as posted")
    else:
        logger.error(f"Failed to post {post_id} to LinkedIn")
    db.close()

def initialize_scheduler():
    jobstore = {
        'default': SQLAlchemyJobStore(url=os.getenv("SCHEDULER_DB_URL"))
    }
    scheduler = BackgroundScheduler(jobstores=jobstore)
    scheduler.start()
    logger.info("Scheduler initialized and started")
    return scheduler

if __name__ == "__main__":
    scheduler = initialize_scheduler()
    logger.info("Scheduler worker running")
    try:
        while True:
            time.sleep(60)  # Keep process alive
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler worker shut down")