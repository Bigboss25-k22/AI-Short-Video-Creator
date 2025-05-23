from sqlalchemy import Column, String, Integer, Text, Float, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid

# Bảng trung gian cho visual elements
scene_visual_elements = Table(
    'scene_visual_elements',
    Base.metadata,
    Column('scene_id', String(36), ForeignKey('scenes.id')),
    Column('visual_element_id', String(36), ForeignKey('visual_elements.id'))
)

class VideoScript(Base):
    __tablename__ = "video_scripts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    target_audience = Column(String(255))
    total_duration = Column(Integer)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="video_scripts")
    scenes = relationship("Scene", back_populates="script", cascade="all, delete-orphan")
    voice_audios = relationship("VoiceAudio", back_populates="script")

class Scene(Base):
    __tablename__ = "scenes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    script_id = Column(String(36), ForeignKey("video_scripts.id"))
    scene_number = Column(Integer)
    description = Column(Text)
    duration = Column(Integer)
    background_music = Column(String(255))
    voice_over = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    script = relationship("VideoScript", back_populates="scenes")
    visual_elements = relationship("VisualElement", secondary=scene_visual_elements, back_populates="scenes")
    voice_audios = relationship("VoiceAudio", back_populates="scene")

class VisualElement(Base):
    __tablename__ = "visual_elements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    element_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    scenes = relationship("Scene", secondary=scene_visual_elements, back_populates="visual_elements")

class VoiceAudio(Base):
    __tablename__ = "voice_audios"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    script_id = Column(String(36), ForeignKey("video_scripts.id"))
    scene_id = Column(String(36), ForeignKey("scenes.id"))
    audio_url = Column(Text)
    text_content = Column(Text)
    voice_id = Column(String(10))
    speed = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    script = relationship("VideoScript", back_populates="voice_audios")
    scene = relationship("Scene", back_populates="voice_audios") 