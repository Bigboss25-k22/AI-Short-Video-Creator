from sqlalchemy.orm import Session
from app.models.video_script import VideoScript, Scene, VoiceAudio, SceneImage, ScriptStatus
from app.schemas.video_script import CreateScriptRequest
from typing import List, Dict, Any, Optional
import uuid

def create_script(db: Session, request: CreateScriptRequest) -> VideoScript:
    """Tạo mới một kịch bản video"""
    db_script = VideoScript(
        title=request.topic,
        description="",
        target_audience=request.target_audience,
        total_duration=request.duration,
        status=ScriptStatus.DRAFT.value  # Sử dụng giá trị của enum
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    return db_script

def get_script(db: Session, script_id: str) -> VideoScript:
    """Lấy thông tin một kịch bản video"""
    return db.query(VideoScript).filter(VideoScript.id == script_id).first()

def get_scripts(db: Session, skip: int = 0, limit: int = 100) -> List[VideoScript]:
    """Lấy danh sách các kịch bản video"""
    return db.query(VideoScript).offset(skip).limit(limit).all()

def update_script(db: Session, script_id: str, update_data: Dict[str, Any]) -> VideoScript:
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

def get_scene(db: Session, scene_id: str) -> Scene:
    """Lấy thông tin một cảnh trong kịch bản"""
    return db.query(Scene).filter(Scene.id == scene_id).first()

def create_scene(db: Session, script_id: str, scene_data: Dict[str, Any]) -> Scene:
    """Tạo mới một cảnh trong kịch bản"""
    db_scene = Scene(
        script_id=script_id,
        **scene_data
    )
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene

def create_voice_audio(db: Session, scene_id: str, audio_data: Dict[str, Any]) -> VoiceAudio:
    """Tạo mới một file audio cho cảnh"""
    db_voice = VoiceAudio(
        scene_id=scene_id,
        **audio_data
    )
    db.add(db_voice)
    db.commit()
    db.refresh(db_voice)
    return db_voice

def create_scene_image(db: Session, scene_id: str, image_data: Dict[str, Any]) -> SceneImage:
    db_image = SceneImage(
        scene_id=scene_id,
        **image_data
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image

def get_scripts_by_user(
    db: Session,
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[ScriptStatus] = None
) -> List[VideoScript]:
    """Lấy danh sách kịch bản video của một người dùng"""
    query = db.query(VideoScript).filter(VideoScript.creator_id == user_id)
    
    if status:
        query = query.filter(VideoScript.status == status)
    
    return query.offset(skip).limit(limit).all() 