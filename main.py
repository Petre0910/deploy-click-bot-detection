# Main FastAPI app
from fastapi import FastAPI, Request, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from services.database import get_db, save_click, save_link, get_link_by_id, get_email_id_by_link_id, get_link_click_stats, get_all_email_ids, get_clicks_by_link_id
from services.bot_detection import is_bot
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from starlette.templating import Jinja2Templates
import uuid
import asyncio
import csv
from io import StringIO
from datetime import datetime


app = FastAPI()

templates = Jinja2Templates(directory="templates")

class LinkData(BaseModel):
    url: str
    utm: str = None
    email_id: str

def generate_unique_id():
    return str(uuid.uuid4())[:8]

@app.post("/create-link")
def create_tracking_link(data: LinkData, db: Session = Depends(get_db)):
    """Generate a short tracking link for an email campaign."""
    link_id = generate_unique_id()
    tracking_link = save_link(link_id, data.url, data.utm, data.email_id)

    return {"tracking_url": f"http://127.0.0.1:8000/{tracking_link.link_id}"}

@app.get("/email-ids")
async def get_email_ids(db: Session = Depends(get_db)):
    """Fetch all distinct email_ids."""
    email_ids = get_all_email_ids(db)
    return {"email_ids": [email_id[0] for email_id in email_ids]}  # Convert tuple to list

@app.get("/dashboard")
async def dashboard(request: Request):
    """Render the dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/{link_id}")
async def track_click(link_id: str, request: Request, db: Session = Depends(get_db)):
    """Processes clicks, detects bots, and redirects accordingly."""

    link = get_link_by_id(link_id, db)

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    #print(request.headers)
    user_ip = request.client.host
    user_agent = request.headers.get("User-Agent")

    print(request.headers)


    email_id = get_email_id_by_link_id(link_id, db)
    is_fraud, fraud_reason = is_bot(user_ip, user_agent, request.headers, email_id, db)    

    save_click(link_id, user_ip, user_agent, is_fraud, fraud_reason, db)    
    
    if is_fraud:
        return RedirectResponse(url= link.destination)
    else:
        return RedirectResponse(url=f"{link.destination}?{link.utm}")


@app.websocket("/ws/{email_id}")
async def websocket_endpoint(websocket: WebSocket, email_id: str, start_date: datetime = None, end_date: datetime = None, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            # Fetch stats periodically or whenever a new click happens
            stats = get_link_click_stats(email_id, db, start_date, end_date)
            await websocket.send_json({"stats": stats})
            await asyncio.sleep(5)  # Update every 5 seconds, adjust as needed
    except WebSocketDisconnect:
        print(f"Client disconnected: {email_id}")


@app.get("/export-link-csv/{link_id}")
async def export_link_to_csv(link_id: str, start_date: datetime = None, end_date: datetime = None, db: Session = Depends(get_db)):
    """Exports click stats for a specific link as CSV."""
    clicks_data = get_clicks_by_link_id(link_id, db, start_date, end_date)
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['ID', 'IP Address', 'User Agent', 'Is Bot', 'Click Time', 'Fraud Reason'])

    # Write click data
    for click in clicks_data:
        writer.writerow([
            click.id,
            click.ip_address,
            click.user_agent,
            click.is_bot,
            click.click_at,
            click.fraud_reason
        ])

    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={link_id}_clicks.csv"})