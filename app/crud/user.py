from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate


def create_user(db: Session, user: UserCreate):
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=user.password,  # Đảm bảo đã hash trước khi lưu!
        role=getattr(user, "role", "user"),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()
