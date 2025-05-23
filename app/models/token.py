from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
import uuid


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    user_id = Column(String(36), ForeignKey("users.id"))

    user = relationship("User", back_populates="refresh_tokens")
