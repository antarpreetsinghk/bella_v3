# app/db/models/appointments.py

from __future__ import annotations
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        sa.UniqueConstraint("user_id", "starts_at", name="uq_appointments_user_id_starts_at"),
        sa.Index("ix_appointments_user_id", "user_id"),
        sa.Index("ix_appointments_starts_at", "starts_at"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Store as timezone-aware UTC
    starts_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    duration_min: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="30")
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False, server_default="booked")
    notes: Mapped[str | None] = mapped_column(sa.Text)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("timezone('utc', now())"),
        nullable=False,
    )

    # Relations
    user: Mapped["User"] = relationship(back_populates="appointments")
