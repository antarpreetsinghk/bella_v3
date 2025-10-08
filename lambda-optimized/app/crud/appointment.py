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
    # Check if appointment already exists (within 1-minute window to handle datetime precision)
    from datetime import timedelta
    time_window_start = starts_at_utc - timedelta(minutes=1)
    time_window_end = starts_at_utc + timedelta(minutes=1)

    existing = await db.execute(
        sa.select(Appointment).where(
            Appointment.user_id == user_id,
            Appointment.starts_at >= time_window_start,
            Appointment.starts_at <= time_window_end
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Appointment already exists for this user at that time.")

    # Ensure timezone-aware datetime for database compatibility
    if starts_at_utc.tzinfo is None:
        # If timezone-naive, assume UTC and make it timezone-aware
        starts_at_utc = starts_at_utc.replace(tzinfo=timezone.utc)

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

async def get_appointment_by_id(
    db: AsyncSession,
    appointment_id: int,
    user_id: Optional[int] = None
) -> Optional[Appointment]:
    """Get appointment by ID, optionally filtered by user"""
    q = sa.select(Appointment).where(Appointment.id == appointment_id)
    if user_id is not None:
        q = q.where(Appointment.user_id == user_id)
    result = await db.execute(q)
    return result.scalar_one_or_none()

async def get_user_appointments(
    db: AsyncSession,
    user_id: int,
    include_cancelled: bool = False,
    future_only: bool = True,
    limit: int = 10
) -> Sequence[Appointment]:
    """Get appointments for a specific user with filtering options"""
    q = sa.select(Appointment).where(Appointment.user_id == user_id)

    if not include_cancelled:
        q = q.where(Appointment.status != "cancelled")

    if future_only:
        q = q.where(Appointment.starts_at > datetime.now(timezone.utc))

    q = q.order_by(Appointment.starts_at.asc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()

async def update_appointment(
    db: AsyncSession,
    appointment_id: int,
    *,
    user_id: Optional[int] = None,
    starts_at_utc: Optional[datetime] = None,
    duration_min: Optional[int] = None,
    notes: Optional[str] = None
) -> Optional[Appointment]:
    """Update an existing appointment"""
    # Get the appointment
    appointment = await get_appointment_by_id(db, appointment_id, user_id)
    if not appointment:
        return None

    # Check if appointment can be modified
    if not appointment.can_be_modified:
        raise ValueError("Appointment cannot be modified (cancelled or in the past)")

    # Check for conflicts if changing time
    if starts_at_utc and starts_at_utc != appointment.starts_at:
        # Ensure timezone-aware datetime
        if starts_at_utc.tzinfo is None:
            starts_at_utc = starts_at_utc.replace(tzinfo=timezone.utc)

        # Check for existing appointments at new time
        from datetime import timedelta
        time_window_start = starts_at_utc - timedelta(minutes=1)
        time_window_end = starts_at_utc + timedelta(minutes=1)

        existing = await db.execute(
            sa.select(Appointment).where(
                Appointment.user_id == appointment.user_id,
                Appointment.id != appointment_id,  # Exclude current appointment
                Appointment.starts_at >= time_window_start,
                Appointment.starts_at <= time_window_end,
                Appointment.status != "cancelled"
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Another appointment already exists at that time")

    # Update fields
    if starts_at_utc is not None:
        appointment.starts_at = starts_at_utc
    if duration_min is not None:
        appointment.duration_min = duration_min
    if notes is not None:
        appointment.notes = notes

    # Mark as modified
    appointment.mark_as_modified()

    try:
        await db.commit()
        await db.refresh(appointment)
        return appointment
    except IntegrityError:
        await db.rollback()
        raise ValueError("Failed to update appointment")

async def cancel_appointment(
    db: AsyncSession,
    appointment_id: int,
    *,
    user_id: Optional[int] = None,
    reason: Optional[str] = None
) -> Optional[Appointment]:
    """Cancel an existing appointment (soft delete)"""
    # Get the appointment
    appointment = await get_appointment_by_id(db, appointment_id, user_id)
    if not appointment:
        return None

    # Check if already cancelled
    if not appointment.is_active:
        raise ValueError("Appointment is already cancelled")

    # Mark as cancelled
    appointment.mark_as_cancelled(reason)

    try:
        await db.commit()
        await db.refresh(appointment)
        return appointment
    except IntegrityError:
        await db.rollback()
        raise ValueError("Failed to cancel appointment")

async def find_appointment_by_phone_and_time(
    db: AsyncSession,
    phone: str,
    starts_at_utc: datetime,
    time_tolerance_minutes: int = 30
) -> Optional[Appointment]:
    """Find appointment by phone number and approximate time for voice lookup"""
    from datetime import timedelta
    from app.crud.user import get_user_by_mobile

    # Find user by phone
    user = await get_user_by_mobile(db, phone)
    if not user:
        return None

    # Search within time window
    time_window_start = starts_at_utc - timedelta(minutes=time_tolerance_minutes)
    time_window_end = starts_at_utc + timedelta(minutes=time_tolerance_minutes)

    q = sa.select(Appointment).where(
        Appointment.user_id == user.id,
        Appointment.starts_at >= time_window_start,
        Appointment.starts_at <= time_window_end,
        Appointment.status != "cancelled"
    ).order_by(
        # Order by closest time match
        sa.func.abs(sa.extract('epoch', Appointment.starts_at - starts_at_utc))
    )

    result = await db.execute(q)
    return result.scalar_one_or_none()
