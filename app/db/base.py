# app/db/base.py

"""
This file imports all the ORM models so Alembic can discover them.
Whenever you add a new model (e.g., User, Appointment, etc.), import it here.
"""
from app.db.models.user import User
from app.db.models.appointment import Appointment
from app.db.session import engine, Base

async def init_db():
    """Initialize database by creating all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def get_engine():
    """Get database engine for connection testing"""
    return engine