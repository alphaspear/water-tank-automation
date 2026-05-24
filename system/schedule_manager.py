from database import SessionLocal
from sqlalchemy import text


# =====================================================
# GET ALL SCHEDULES
# =====================================================

def get_schedules():

    db = SessionLocal()

    result = db.execute(
        text("""
            SELECT *
            FROM schedules
            WHERE enabled = true
            ORDER BY start_time
        """)
    )

    schedules = result.mappings().all()

    db.close()

    return schedules


# =====================================================
# CREATE SCHEDULE
# =====================================================

def create_schedule(
    name,
    schedule_type,
    start_time,
    duration_seconds=None
):

    db = SessionLocal()

    db.execute(
        text("""
            INSERT INTO schedules (
                name,
                schedule_type,
                start_time,
                duration_seconds
            )
            VALUES (
                :name,
                :schedule_type,
                :start_time,
                :duration_seconds
            )
        """),
        {
            "name": name,
            "schedule_type": schedule_type,
            "start_time": start_time,
            "duration_seconds": duration_seconds,
        }
    )

    db.commit()

    db.close()


# =====================================================
# DELETE SCHEDULE
# =====================================================

def delete_schedule(schedule_id):

    db = SessionLocal()

    db.execute(
        text("""
            DELETE FROM schedules
            WHERE id = :id
        """),
        {
            "id": schedule_id
        }
    )

    db.commit()

    db.close()