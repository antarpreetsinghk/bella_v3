# app/db/base.py

"""
This file imports all the ORM models so Alembic can discover them.
Whenever you add a new model (e.g., User, Appointment, etc.), import it here.
"""
from app.db.models.user import User
from app.db.models.appointment import Appointment