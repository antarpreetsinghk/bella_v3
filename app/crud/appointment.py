# app/crud/appointment.py

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

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
    # Check if appointment already exists
    existing = await db.execute(
        sa.select(Appointment).where(
            Appointment.user_id == user_id,
            Appointment.starts_at == starts_at_utc
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Appointment already exists for this user at that time.")

    # Create new appointment with explicit timestamp
    appt = Appointment(
        user_id=user_id,
        starts_at=starts_at_utc,
        duration_min=duration_min,
        status=status,
        notes=notes,
        created_at=datetime.now(timezone.utc)  # Explicit timezone-aware timestamp
    )
    db.add(appt)

    try:
        await db.commit()
        await db.refresh(appt)
        return appt
    except IntegrityError:
        await db.rollback()
        raise ValueError("Appointment already exists for this user at that time.")

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
