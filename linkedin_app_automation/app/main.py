
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os, uuid
from io import BytesIO
import pandas as pd
from app.groq import enhance_content, generate_content
from fastapi import Form
from app.linkedin import get_linkedin_user_id, post_to_linkedin
from app.database import ScheduledPost, SessionLocal
from datetime import datetime
import json

from app.scheduler import add_job
from dotenv import load_dotenv
import os

with open("app/config.json") as f:
    config = json.load(f)

app = FastAPI()
# app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

load_dotenv()

UPLOAD_DIR = "uploaded"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload_step.html", {
        "request": request,
        "filename": None
    })

# @app.post("/upload", response_class=HTMLResponse)
# async def upload_file(request: Request, file: UploadFile):
#     unique_name = f"{uuid.uuid4()}.xlsx"
#     path = os.path.join(UPLOAD_DIR, unique_name)

#     with open(path, "wb") as f:
#         f.write(await file.read())

#     return templates.TemplateResponse("upload_step.html", {
#         "request": request,
#         "filename": unique_name
#     })

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile):
    unique_name = f"{uuid.uuid4()}.xlsx"
    path = os.path.join(UPLOAD_DIR, unique_name)

    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)

    # Load Excel and convert to HTML
    df = pd.read_excel(BytesIO(contents))
    preview_html = df.head(10).to_html(index=False, classes="excel-preview")

    return templates.TemplateResponse("upload_step.html", {
        "request": request,
        "filename": unique_name,
        "preview": preview_html
    })


@app.post("/process", response_class=HTMLResponse)
async def process_file(
    request: Request,
    action: str = Form(...),
    filename: str = Form(...)
):
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        return templates.TemplateResponse("upload_step.html", {
            "request": request,
            "filename": None,
            "error": "Uploaded file not found. Please upload again."
        })

    df = pd.read_excel(file_path)
    results = []

    for _, row in df.iterrows():
        text = str(row.get("Text", "")).strip()
        typ = str(row.get("Type", "")).strip().lower()
        image = row.get("image", "")

        if not text or not typ:
            continue

        # 👇 Enhancement logic
        if action == "enhance" and typ == "content":
            enhanced = enhance_content(text)
            results.append({"type": typ, "input": text, "output": enhanced, "image": image})

        # 👇 Generation logic
        elif action == "generate" and typ == "prompt":
            for variation, i in generate_content(text, 3):
                results.append({"type": typ, "input": text, "output": variation, "variation": i, "image": image})

    os.remove(file_path)

    return templates.TemplateResponse("result_step.html", {
        "request": request,
        "results": results,
        "action": action
    })


@app.post("/handle_post_action", response_class=HTMLResponse)
async def handle_post_action(
    request: Request,
    action: str = Form(...),
    output: str = Form(...),
    input: str = Form(...),
    image: str = Form(""),
    variation: str = Form(""),
    schedule_time: str = Form("")
):
    message = ""
    access_token = os.getenv["LINKEDIN_ACCESS_TOKEN"]
    user_id = get_linkedin_user_id(access_token)

    if action == "post":
        success = post_to_linkedin(output, access_token, user_id, image)
        message = "✅ Posted to LinkedIn!" if success else "❌ Failed to post."

    elif action == "schedule":
        if schedule_time:
            try:
                run_dt = datetime.fromisoformat(schedule_time)
                post_id = str(uuid.uuid4())

                # 1. Save to DB
                db = SessionLocal()
                db.add(ScheduledPost(
                    post_id=post_id,
                    text=output,
                    image_url=image,
                    scheduled_datetime=schedule_time,
                    posted=False
                ))
                db.commit()
                db.close()

                # 2. Schedule the job
                add_job(post_id, output, image, run_dt)

                message = f"🕒 Scheduled for {schedule_time}"
            except Exception as e:
                message = f"❌ Error scheduling post: {str(e)}"
        else:
            message = "⚠ Please select a schedule time."

    elif action == "edit":
        message = "✏ Edited successfully! You can now post or schedule."

    return templates.TemplateResponse("single_result.html", {
        "request": request,
        "output": output,
        "input": input,
        "variation": variation,
        "image": image,
        "message": message
    })


@app.get("/scheduled", response_class=HTMLResponse)
async def scheduled_dashboard(request: Request):
    db = SessionLocal()
    posts = db.query(ScheduledPost).order_by(ScheduledPost.scheduled_datetime.desc()).all()
    db.close()
    return templates.TemplateResponse("scheduled_dashboard.html", {
        "request": request,
        "posts": posts
    })
