# app/crud/appointment.py

from __future__ import annotations
from datetime import datetime
from typing import Optional, Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.db.models.appointment import Appointment

UNIQUE_COLS = ["user_id", "starts_at"]

async def create_appointment_unique(
    db: AsyncSession,
    *,
    user_id: int,
    starts_at_utc: datetime,
    duration_min: int = 30,
    status: str = "booked",
    notes: Optional[str] = None,
) -> Appointment:
    stmt = (
        insert(Appointment)
        .values(
            user_id=user_id,
            starts_at=starts_at_utc,
            duration_min=duration_min,
            status=status,
            notes=notes,
        )
        .returning(Appointment)              # ORM row back
        .on_conflict_do_nothing(index_elements=UNIQUE_COLS)
    )
    res = await db.execute(stmt)
    row = res.fetchone()
    if row is None:
        # conflict occurred
        await db.rollback()
        raise ValueError("Appointment already exists for this user at that time.")
    await db.commit()
    return row[0]

async def list_appointments(
    db: AsyncSession,
    *,
    user_id: Optional[int] = None,
    start_utc: Optional[datetime] = None,
    end_utc: Optional[datetime] = None,
    limit: int = 100,
) -> Sequence[Appointment]:
    q = sa.select(Appointment)
    if user_id is not None:
        q = q.where(Appointment.user_id == user_id)
    if start_utc is not None:
        q = q.where(Appointment.starts_at >= start_utc)
    if end_utc is not None:
        q = q.where(Appointment.starts_at < end_utc)
    q = q.order_by(Appointment.starts_at.asc()).limit(limit)
    res = await db.execute(q)
    return res.scalars().all()
