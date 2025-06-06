from sqlalchemy import Column, String, Integer, Text, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum

class ScriptStatus(enum.Enum):
    DRAFT = "draft"  # Script mới được tạo
    PROCESSING = "processing"  # Đang xử lý tạo hình ảnh và voice
    COMPLETED = "completed"  # Đã hoàn thành tất cả
    FAILED = "failed"  # Có lỗi xảy ra

class MediaStatus(enum.Enum):
    PENDING = "pending"  # Chưa bắt đầu xử lý
    PROCESSING = "processing"  # Đang xử lý
    COMPLETED = "completed"  # Đã hoàn thành
    FAILED = "failed"  # Có lỗi xảy ra

class VideoScript(Base):
    __tablename__ = "video_scripts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    target_audience = Column(String(255))
    total_duration = Column(Integer)
    status = Column(String(20), default=ScriptStatus.DRAFT.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="video_scripts")
    scenes = relationship("Scene", back_populates="script", cascade="all, delete-orphan")

class Scene(Base):
    __tablename__ = "scenes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    script_id = Column(String(36), ForeignKey("video_scripts.id"))
    scene_number = Column(Integer)
    description = Column(Text)
    duration = Column(Integer)
    visual_elements = Column(Text)  # Mô tả chi tiết cho việc tạo hình ảnh
    background_music = Column(String(255))
    voice_over = Column(Text)
    image_status = Column(String(20), default=MediaStatus.PENDING.value)
    voice_status = Column(String(20), default=MediaStatus.PENDING.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    script = relationship("VideoScript", back_populates="scenes")
    voice_audios = relationship("VoiceAudio", back_populates="scene", cascade="all, delete-orphan")
    images = relationship("SceneImage", back_populates="scene", cascade="all, delete-orphan")

class VoiceAudio(Base):
    __tablename__ = "voice_audios"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scene_id = Column(String(36), ForeignKey("scenes.id"))
    audio_url = Column(Text)
    text_content = Column(Text)
    voice_id = Column(String(20))
    speed = Column(Float)
    status = Column(String(20), default=MediaStatus.PENDING.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    scene = relationship("Scene", back_populates="voice_audios")

class SceneImage(Base):
    __tablename__ = "scene_images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scene_id = Column(String(36), ForeignKey("scenes.id"))
    image_url = Column(Text)  # URL của hình ảnh được tạo
    prompt = Column(Text)  # Prompt được sử dụng để tạo hình ảnh
    width = Column(Integer, default=1024)  # Chiều rộng hình ảnh
    height = Column(Integer, default=768)  # Chiều cao hình ảnh
    status = Column(String(20), default=MediaStatus.PENDING.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    scene = relationship("Scene", back_populates="images") 