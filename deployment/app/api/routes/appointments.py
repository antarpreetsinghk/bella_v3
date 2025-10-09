# app/api/routes/appointments.py

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.appointment import AppointmentCreate, AppointmentOut
from app.crud.user import get_user_by_mobile, create_user
from app.crud.appointment import create_appointment_unique, list_appointments
from app.schemas.user import UserCreate

router = APIRouter(prefix="/appointments", tags=["appointments"])

LOCAL_TZ = ZoneInfo("America/Edmonton")
UTC = ZoneInfo("UTC")

def parse_to_utc(s: str) -> datetime:
    # Accepts ISO8601 with tz or naive datetime string treated as LOCAL_TZ
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        raise HTTPException(status_code=422, detail="starts_at must be ISO8601 (e.g., 2025-08-28 10:00)")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(UTC)

@router.post("", response_model=AppointmentOut, status_code=201)
async def book_appointment(payload: AppointmentCreate, db: AsyncSession = Depends(get_session)):
    # 1) find-or-create user by mobile
    user = await get_user_by_mobile(db, payload.mobile)
    if not user:
        # fall back name if not provided
        user = await create_user(
            db,
            data=UserCreate(
                full_name=payload.full_name or "Unknown",
                mobile=payload.mobile,
            ),
        )

    # 2) parse local/ISO → UTC
    starts_at_utc = parse_to_utc(payload.starts_at)

    # 3) create appointment with unique guard
    try:
        appt = await create_appointment_unique(
            db,
            user_id=user.id,
            starts_at_utc=starts_at_utc,
            duration_min=payload.duration_min,
            notes=payload.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {
        "id": appt.id,
        "user_id": appt.user_id,
        "starts_at_utc": appt.starts_at,
        "duration_min": appt.duration_min,
        "status": appt.status,
        "notes": appt.notes,
    }

@router.get("", response_model=List[AppointmentOut])
async def get_appointments(
    db: AsyncSession = Depends(get_session),
    mobile: Optional[str] = Query(None, description="Filter by user mobile"),
    start: Optional[str] = Query(None, description="Start (local/ISO)"),
    end: Optional[str] = Query(None, description="End (local/ISO)"),
    limit: int = 100,
):
    user_id = None
    if mobile:
        u = await get_user_by_mobile(db, mobile)
        if not u:
            return []
        user_id = u.id

    def p(s: Optional[str]) -> Optional[datetime]:
        return parse_to_utc(s) if s else None

    rows = await list_appointments(
        db,
        user_id=user_id,
        start_utc=p(start),
        end_utc=p(end),
        limit=limit,
    )
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "starts_at_utc": r.starts_at,
            "duration_min": r.duration_min,
            "status": r.status,
            "notes": r.notes,
        }
        for r in rows
    ]
