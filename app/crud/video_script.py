from sqlalchemy.orm import Session
from app.models.video_script import VideoScript, Scene, VoiceAudio
from app.schemas.video_script import CreateScriptRequest
from typing import List, Optional
import uuid

def create_script(db: Session, request: CreateScriptRequest) -> VideoScript:
    """Tạo mới một kịch bản video"""
    db_script = VideoScript(
        id=str(uuid.uuid4()),
        title=request.topic,  # Sử dụng topic làm title
        description="",  # Sẽ được cập nhật sau khi tạo
        target_audience=request.target_audience,
        total_duration=request.duration,
        status="draft"
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    return db_script

def get_script(db: Session, script_id: str) -> Optional[VideoScript]:
    """Lấy thông tin một kịch bản video"""
    return db.query(VideoScript).filter(VideoScript.id == script_id).first()

def get_scripts(db: Session, skip: int = 0, limit: int = 100) -> List[VideoScript]:
    """Lấy danh sách các kịch bản video"""
    return db.query(VideoScript).offset(skip).limit(limit).all()

def update_script(db: Session, script_id: str, update_data: dict) -> Optional[VideoScript]:
    """Cập nhật thông tin kịch bản video"""
    db_script = get_script(db, script_id)
    if db_script:
        for key, value in update_data.items():
            setattr(db_script, key, value)
        db.commit()
        db.refresh(db_script)
    return db_script

def delete_script(db: Session, script_id: str) -> bool:
    """Xóa một kịch bản"""
    db_script = get_script(db, script_id)
    if db_script:
        db.delete(db_script)
        db.commit()
        return True
    return False

def create_scene(db: Session, script_id: str, scene_data: dict) -> Scene:
    """Tạo mới một cảnh trong kịch bản"""
    db_scene = Scene(
        id=str(uuid.uuid4()),
        script_id=script_id,
        **scene_data
    )
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene

def create_voice_audio(db: Session, script_id: str, scene_id: str, audio_data: dict) -> VoiceAudio:
    """Tạo mới một file audio cho cảnh"""
    db_audio = VoiceAudio(
        id=str(uuid.uuid4()),
        script_id=script_id,
        scene_id=scene_id,
        **audio_data
    )
    db.add(db_audio)
    db.commit()
    db.refresh(db_audio)
    return db_audio 