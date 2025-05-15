from app.models.user import users
from app.schemas.user import UserCreate
from sqlalchemy import select, insert, update, delete
from app.core.database import database


async def create_user(user: UserCreate):
    query = users.insert().values(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
    )
    user_id = await database.execute(query)
    return {**user.dict(), "id": user_id}


async def get_user(user_id: int):
    query = select(users).where(users.c.id == user_id)
    return await database.fetch_one(query)
