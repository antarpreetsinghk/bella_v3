# app/schemas/appointment.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

class AppointmentCreate(BaseModel):
    full_name: Optional[str] = Field(None, examples=["Jane Doe"])  # used if user not found
    mobile: str = Field(..., examples=["+1-587-555-0123"])
    starts_at: str = Field(..., description="Local (America/Edmonton) or ISO8601 datetime")
    duration_min: int = 30
    notes: Optional[str] = None

class AppointmentOut(BaseModel):
    id: int
    user_id: int
    starts_at_utc: datetime
    duration_min: int
    status: str
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
