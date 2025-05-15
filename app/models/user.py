from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base  # Phải import Base, không phải metadata
import enum


class RoleEnum(str, enum.Enum):
    user = "user"
    admin = "admin"


class User(Base):  # Kế thừa từ Base
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    hashed_password = Column(String(128), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.user)

    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
