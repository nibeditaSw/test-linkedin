# # app/scheduler.py
# from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
# from app.database import SessionLocal, ScheduledPost
# from app.linkedin import get_linkedin_user_id, post_to_linkedin
# import json, logging
# from datetime import datetime
# from dotenv import load_dotenv
# import os

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# load_dotenv()

# with open("app/config.json") as f:
#     config = json.load(f)

# def scheduled_job(post_id, text, image_url):
#     logger.info(f"Scheduler triggered for post {post_id}")
#     access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
#     user_id = get_linkedin_user_id(access_token)
#     if not user_id:
#         logger.error("Cannot get LinkedIn user ID")
#         return
#     success = post_to_linkedin(text, access_token, user_id, image_url)
#     db = SessionLocal()
#     post = db.query(ScheduledPost).filter_by(post_id=post_id).first()
#     if post and success:
#         post.posted = True
#         db.commit()
#     db.close()

# def add_job(post_id, text, image_url, run_datetime):
#     scheduler.add_job(
#         scheduled_job,
#         "date",
#         run_date=run_datetime,
#         args=[post_id, text, image_url],
#         id=post_id,
#         replace_existing=True
#     )
#     logger.info(f"Job scheduled: {post_id} at {run_datetime}")

# jobstore = {
#     'default': SQLAlchemyJobStore(url='sqlite:///./jobs.sqlite')
# }
# scheduler = BackgroundScheduler(jobstores=jobstore)
# scheduler.start()


# linkedin_app_automation/app/scheduler.py
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from app.database import SessionLocal, ScheduledPost
from app.linkedin import get_linkedin_user_id, post_to_linkedin
from datetime import datetime
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
scheduler = None

def job_listener(event):
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    else:
        logger.info(f"Job {event.job_id} executed successfully")

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
    try:
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
    except Exception as e:
        logger.error(f"Error in scheduled_job for {post_id}: {str(e)}")
        db.close()

def initialize_scheduler():
    global scheduler
    if scheduler is None or not scheduler.running:
        jobstore_url = os.getenv("SCHEDULER_DB_URL")
        if not jobstore_url:
            logger.error("SCHEDULER_DB_URL is not set")
            raise ValueError("SCHEDULER_DB_URL is required")
        jobstore = {'default': SQLAlchemyJobStore(url=jobstore_url)}
        scheduler = BackgroundScheduler(jobstores=jobstore)
        scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        scheduler.start()
        logger.info("Scheduler initialized and started")
    else:
        logger.info("Scheduler already running")
    return scheduler

def add_job(post_id, text, image_url, run_datetime):
    global scheduler
    initialize_scheduler()
    scheduler.add_job(
        scheduled_job,
        "date",
        run_date=run_datetime,
        args=[post_id, text, image_url],
        id=post_id,
        replace_existing=True
    )
    logger.info(f"Job scheduled: {post_id} at {run_datetime}")
    logger.debug(f"Current jobs: {scheduler.get_jobs()}")
