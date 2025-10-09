# app/db/models/appointments.py

from __future__ import annotations
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        sa.Index("ix_appointments_user_id", "user_id"),
        sa.Index("ix_appointments_starts_at", "starts_at"),
        sa.Index("ix_appointments_google_event_id", "google_event_id"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Store as timezone-aware UTC
    starts_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    duration_min: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="30")
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False, server_default="booked")
    notes: Mapped[str | None] = mapped_column(sa.Text)

    # Appointment lifecycle management
    cancelled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    modified_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    modification_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")

    # Google Calendar integration
    google_event_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)  # Python-side timezone-aware default
    )

    # Relations
    user: Mapped["User"] = relationship(back_populates="appointments")

    # Helper properties
    @property
    def is_active(self) -> bool:
        """Check if appointment is active (not cancelled)"""
        return self.status != "cancelled" and self.cancelled_at is None

    @property
    def can_be_modified(self) -> bool:
        """Check if appointment can still be modified"""
        if not self.is_active:
            return False
        # Can't modify past appointments
        return self.starts_at > datetime.now(timezone.utc)

    def mark_as_cancelled(self, reason: str = None):
        """Mark appointment as cancelled"""
        self.status = "cancelled"
        self.cancelled_at = datetime.now(timezone.utc)
        if reason:
            self.notes = f"Cancelled: {reason}" if not self.notes else f"{self.notes}\nCancelled: {reason}"

    def mark_as_modified(self):
        """Mark appointment as modified"""
        self.modified_at = datetime.now(timezone.utc)
        self.modification_count += 1
