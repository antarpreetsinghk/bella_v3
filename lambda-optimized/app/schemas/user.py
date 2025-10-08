# app/schemas/user.py
from datetime import date as _Date, datetime as _Datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class UserBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)
    mobile: str = Field(..., min_length=7, max_length=20)
    date: Optional[_Date] = None  # optional appointment/request date

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        # trim + collapse internal extra spaces
        v = " ".join(v.strip().split())
        if not v:
            raise ValueError("full_name cannot be empty")
        return v

    @field_validator("mobile")
    @classmethod
    def _normalize_mobile(cls, v: str) -> str:
        # keep leading '+', remove spaces/dashes; enforce digits length 7–15
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("+"):
            d = v[1:]
            if not d.isdigit() or not (7 <= len(d) <= 15):
                raise ValueError("mobile must be + followed by 7–15 digits")
            return "+" + d
        if not v.isdigit() or not (7 <= len(v) <= 15):
            raise ValueError("mobile must be 7–15 digits")
        return v

class UserCreate(UserBase):
    """Incoming payload for creating a user."""
    pass

class UserOut(UserBase):
    """Response model for reading a user."""
    id: int
    created_at: _Datetime

    class Config:
        from_attributes = True  # allow returning ORM objects directly

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    date: Optional[_Date] = None

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = " ".join(v.strip().split())
        if not v:
            raise ValueError("full_name cannot be empty")
        return v

    @field_validator("mobile")
    @classmethod
    def _normalize_mobile(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().replace(" ", "").replace("-", "")
        if v.startswith("+"):
            d = v[1:]
            if not d.isdigit() or not (7 <= len(d) <= 15):
                raise ValueError("mobile must be + followed by 7–15 digits")
            return "+" + d
        if not v.isdigit() or not (7 <= len(v) <= 15):
            raise ValueError("mobile must be 7–15 digits")
        return v
