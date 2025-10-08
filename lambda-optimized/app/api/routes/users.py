# app/api/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.crud.user import (
    create_user, get_user, list_users, delete_user, get_user_by_mobile, update_user
)

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user_ep(payload: UserCreate, db: AsyncSession = Depends(get_session)):
    try:
        return await create_user(db, payload)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="mobile already exists")

# (Optional) lookup by mobile — keep static route above the param route for clarity
@router.get("/by-mobile", response_model=UserOut)
async def get_by_mobile_ep(mobile: str, db: AsyncSession = Depends(get_session)):
    obj = await get_user_by_mobile(db, mobile)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj

@router.get("/{user_id}", response_model=UserOut)
async def get_user_ep(user_id: int, db: AsyncSession = Depends(get_session)):
    obj = await get_user(db, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj

@router.get("", response_model=list[UserOut])
async def list_users_ep(limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_session)):
    return await list_users(db, limit=limit, offset=offset)

@router.patch("/{user_id}", response_model=UserOut)
async def update_user_ep(user_id: int, payload: UserUpdate, db: AsyncSession = Depends(get_session)):
    try:
        obj = await update_user(db, user_id, payload)
    except IntegrityError:
        # e.g., trying to change mobile to an existing one
        raise HTTPException(status_code=409, detail="mobile already exists")
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_ep(user_id: int, db: AsyncSession = Depends(get_session)):
    ok = await delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
