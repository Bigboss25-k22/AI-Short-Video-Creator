from fastapi import APIRouter, Depends, HTTPException
from app.schemas.user import User, UserCreate
from app.crud.user import create_user, get_user
from app.core.database import database

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=User)
async def api_create_user(user: UserCreate):
    return await create_user(user)


@router.get("/{user_id}", response_model=User)
async def api_get_user(user_id: int):
    user = await get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Event startup/shutdown để kết nối DB
@router.on_event("startup")
async def startup():
    await database.connect()


@router.on_event("shutdown")
async def shutdown():
    await database.disconnect()
