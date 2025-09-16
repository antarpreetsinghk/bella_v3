# app/db/models/user.py

from datetime import date, datetime
from sqlalchemy.orm import Mapped, mapped_column
import sqlalchemy as sa

from app.db.session import Base  # your declarative Base
from app.db.models.appointment import Appointment

from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    # Primary key: big and auto-incrementing (maps to IDENTITY on modern Postgres)
    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    # Required fields
    full_name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    mobile: Mapped[str] = mapped_column(sa.String(20), nullable=False, unique=True)
    # Server-side timestamp (tz-aware). Postgres will fill this on insert.
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

