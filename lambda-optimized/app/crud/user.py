# app/crud/user.py
from typing import Sequence, Optional
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.models.user import User  # ← consistent with app/models/*
from app.schemas.user import UserCreate, UserUpdate


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    return await db.get(User, user_id)


async def get_user_by_mobile(db: AsyncSession, mobile: str) -> Optional[User]:
    stmt = sa.select(User).where(User.mobile == mobile)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    """
    Insert a new user. If a concurrent request already created the same mobile,
    return the existing user instead of raising on UNIQUE constraint.
    """
    from datetime import datetime, timezone
    obj = User(
        full_name=data.full_name,
        mobile=data.mobile,
        created_at=datetime.now(timezone.utc)  # Explicit timezone-aware timestamp
    )
    db.add(obj)
    try:
        await db.commit()
        await db.refresh(obj)
        return obj
    except IntegrityError:
        await db.rollback()
        existing = await get_user_by_mobile(db, data.mobile)
        if existing:
            return existing
        raise


async def list_users(
    db: AsyncSession, *, limit: int = 100, offset: int = 0
) -> Sequence[User]:
    stmt = sa.select(User).order_by(User.id.desc()).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


async def update_user(db: AsyncSession, user_id: int, data: UserUpdate) -> Optional[User]:
    obj = await db.get(User, user_id)
    if not obj:
        return None

    changes = data.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(obj, k, v)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(obj)
    return obj


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    obj = await db.get(User, user_id)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True
