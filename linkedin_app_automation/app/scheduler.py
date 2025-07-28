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

# app/scheduler.py
import logging
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def add_job(post_id, text, image_url, run_datetime):
    jobstore = {
        'default': SQLAlchemyJobStore(url=os.getenv("SCHEDULER_DB_URL"))
    }
    scheduler = BackgroundScheduler(jobstores=jobstore)
    scheduler.add_job(
        func='app.scheduler_worker:scheduled_job',  # Reference the job in scheduler_worker
        trigger="date",
        run_date=run_datetime,
        args=[post_id, text, image_url],
        id=post_id,
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Job scheduled: {post_id} at {run_datetime}")
    scheduler.shutdown()  # Shutdown immediately after adding job
