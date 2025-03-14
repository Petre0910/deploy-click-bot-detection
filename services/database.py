# PostgreSQL connection
from sqlalchemy import create_engine
from sqlalchemy import func, cast, Integer
from sqlalchemy.orm import sessionmaker
from models.click_model import ClickLog
from models.link_model import TrackingLink
from datetime import datetime, timedelta

DATABASE_URL = "postgresql://postgres.yyfowtywhwmbrtbvdtyx:Covid2019)(!)@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for getting the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_click(link_id, ip_address, user_agent, is_bot, fraud_reason, db):
    """Stores click event in the database using SQLAlchemy."""
    # Verify link_id exists before inserting
    link_exists = db.query(TrackingLink).filter(TrackingLink.link_id == link_id).first()
    if not link_exists:
        print(f"Invalid link_id: {link_id}")
        return  # or raise an errorcls
    
    db = SessionLocal()
    try:
        click = ClickLog(link_id=link_id, ip_address=ip_address, user_agent=user_agent, is_bot=is_bot, fraud_reason = fraud_reason)
        db.add(click)
        db.commit()
        db.refresh(click)
        return click
    finally:
        db.close()

def save_link(link_id, destination, utm, email_id):
    """Saves a new tracking link."""
    db = SessionLocal()
    try:
        link = TrackingLink(link_id=link_id, destination=destination, utm=utm, email_id=email_id)
        db.add(link)
        db.commit()
        db.refresh(link)
        return link
    finally:
        db.close()

def get_click_stats(email_id, db):
    """Returns the count of clicks and the latest click_time in the last 10 seconds for a given email_id."""

    ten_seconds_ago = datetime.utcnow() - timedelta(seconds=10)

    count, last_click_time = db.query(
        func.count(ClickLog.id),
        func.max(ClickLog.click_at)
    ).join(
        TrackingLink, ClickLog.link_id == TrackingLink.link_id
    ).filter(
        TrackingLink.email_id == email_id,
        ClickLog.click_at >= ten_seconds_ago
    ).first()

    return count, last_click_time

def get_link_by_id(link_id: str, db):
    """Fetch the tracking link from the database by link_id."""
    return db.query(TrackingLink).filter(TrackingLink.link_id == link_id).first()

def get_email_id_by_link_id(link_id: str, db):
    """
    Retrieve the email_id associated with a given link_id.
    """
    result = db.query(TrackingLink.email_id).filter(TrackingLink.link_id == link_id).first()
    if result:
        return result[0]  # Return email_id
    return None  # If not found, return None

from sqlalchemy import func

def get_link_click_stats(email_id, db):
    """Fetch click stats (all clicks, bot clicks, human clicks, and percentages) for all links in an email."""
    stats = db.query(
        TrackingLink.link_id,
        func.count(ClickLog.id).label('total_clicks'),
        func.coalesce(func.sum(cast(ClickLog.is_bot, Integer)), 0).label('bot_clicks'),
        (
            func.count(ClickLog.id) - func.coalesce(func.sum(cast(ClickLog.is_bot, Integer)), 0)
        ).label('human_clicks')
    ).join(
        ClickLog, ClickLog.link_id == TrackingLink.link_id
    ).filter(
        TrackingLink.email_id == email_id
    ).group_by(
        TrackingLink.link_id
    ).all()


    # Calculate percentages
    result = []
    for stat in stats:
        total_clicks = stat.total_clicks or 0  # Ensure default to 0
        bot_clicks = stat.bot_clicks or 0
        human_clicks = stat.human_clicks or 0
        bot_percentage = (bot_clicks / total_clicks * 100) if total_clicks > 0 else 0
        human_percentage = (human_clicks / total_clicks * 100) if total_clicks > 0 else 0
        
        result.append({
            'link_id': stat.link_id,
            'total_clicks': total_clicks,
            'bot_clicks': bot_clicks,
            'human_clicks': human_clicks,
            'bot_percentage': round(bot_percentage, 2),
            'human_percentage': round(human_percentage, 2)
        })

    return result


def get_all_email_ids(db):
    """Fetch all distinct email_ids from the TrackingLink table."""
    return db.query(TrackingLink.email_id).distinct().all()