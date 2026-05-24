from sqlalchemy import text

from database import SessionLocal

# =====================================================
# LOG EVENT
# =====================================================

def log_event(
    event_type,
    message
):

    db = SessionLocal()

    db.execute(
        text("""
            INSERT INTO event_logs (
                event_type,
                message
            )
            VALUES (
                :event_type,
                :message
            )
        """),
        {
            "event_type": event_type,
            "message": message,
        }
    )

    db.commit()

    db.close()

# =====================================================
# GET RECENT EVENTS
# =====================================================

def get_recent_events(limit=50):

    db = SessionLocal()

    result = db.execute(
        text("""
            SELECT *
            FROM event_logs
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {
            "limit": limit
        }
    )

    rows = result.mappings().all()

    db.close()

    return rows