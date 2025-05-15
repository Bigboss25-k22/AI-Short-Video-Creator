from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.database import database, engine
from sqlalchemy.orm import sessionmaker

# Tạo sessionmaker cho async
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def create_user(user: UserCreate):
    async with AsyncSessionLocal() as session:
        db_user = User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            hashed_password=user.password,  # Đảm bảo đã hash trước khi lưu!
            role=user.role if hasattr(user, "role") else "user",
        )
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        return db_user


async def get_user(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
