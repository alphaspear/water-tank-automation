from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import yaml
from urllib.parse import quote_plus

# =====================================================
# LOAD CONFIG
# =====================================================

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

db_config = config["database"]

DB_USER = db_config["user"]

DB_PASSWORD = quote_plus(
    db_config["password"]
)

DB_HOST = db_config["host"]

DB_PORT = db_config["port"]

DB_NAME = db_config["name"]

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# =====================================================
# ENGINE
# =====================================================

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =====================================================
# AUTO CREATE TABLES
# =====================================================

def initialize_database():

    db = SessionLocal()

    db.execute(text("""

        CREATE TABLE IF NOT EXISTS schedules (

            id SERIAL PRIMARY KEY,

            name TEXT NOT NULL,

            schedule_type TEXT NOT NULL,

            start_time TIME NOT NULL,

            duration_seconds INTEGER,

            enabled BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );

    """))

    db.execute(text("""

        CREATE TABLE IF NOT EXISTS event_logs (

            id BIGSERIAL PRIMARY KEY,

            event_type TEXT NOT NULL,

            message TEXT NOT NULL,

            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );

    """))

    db.commit()

    db.close()