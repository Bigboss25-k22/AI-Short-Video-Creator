from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from app.schemas.video_script import VideoScript, CreateScriptRequest
from app.services.deepseek_service import DeepSeekService
from app.crud import video_script as crud
from app.database import get_db
from app.models.video_script import ScriptStatus, MediaStatus
from typing import Optional, List
import os
import tempfile
import shutil
from pydantic import BaseModel

router = APIRouter()
deepseek_service = DeepSeekService()

class TextToSpeechRequest(BaseModel):
    text: str
    voice_id: str = "vi-VN-Wavenet-A"  # Vietnamese female voice
    speed: float = 1.0

@router.post("/generate", response_model=VideoScript)
async def generate_video_script(request: CreateScriptRequest, db: Session = Depends(get_db)):
    """
    Tạo kịch bản video tự động dựa trên chủ đề, đối tượng mục tiêu và thời lượng
    """
    db_script = None  # Khởi tạo biến db_script
    try:
        # Tạo nội dung script bằng DeepSeek
        script = deepseek_service.generate_video_script(
            topic=request.topic,
            target_audience=request.target_audience,
            duration=request.duration
        )
        
        # Tạo script trong database với status DRAFT
        db_script = crud.create_script(db, request)
        
        # Cập nhật thông tin script trong database
        crud.update_script(db, db_script.id, {
            "title": script.title,
            "description": script.description,
            "total_duration": script.total_duration,
            "status": ScriptStatus.DRAFT.value  
        })
        
        # Tạo các scene trong database
        for scene in script.scenes:
            # Tạo scene với visual_elements là mô tả chi tiết
            db_scene = crud.create_scene(db, db_script.id, {
                "scene_number": scene.scene_number,
                "description": scene.description,
                "duration": scene.duration,
                "visual_elements": scene.visual_elements,
                "background_music": scene.background_music,
                "voice_over": scene.voice_over,
                "image_status": MediaStatus.PENDING.value,
                "voice_status": MediaStatus.PENDING.value
            })
        
        # Lấy script đã lưu từ database để trả về
        saved_script = crud.get_script(db, db_script.id)
        return saved_script
    except Exception as e:
        # Nếu có lỗi, cập nhật status thành FAILED
        if db_script:
            crud.update_script(db, db_script.id, {"status": ScriptStatus.FAILED.value})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/enhance/{script_id}", response_model=VideoScript)
async def enhance_video_script(script_id: str, db: Session = Depends(get_db)):
    """
    Cải thiện kịch bản video với các đề xuất chi tiết hơn
    """
    try:
        # Lấy script từ database
        db_script = crud.get_script(db, script_id)
        if not db_script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        # Cải thiện script bằng DeepSeek
        enhanced_script = deepseek_service.enhance_script(db_script)
        
        # Cập nhật thông tin trong database
        crud.update_script(db, script_id, {
            "title": enhanced_script.title,
            "description": enhanced_script.description,
            "total_duration": enhanced_script.total_duration
        })
        
        # Xóa các scene cũ
        for scene in db_script.scenes:
            db.delete(scene)
        db.commit()
        
        # Tạo các scene mới với mô tả chi tiết
        for scene in enhanced_script.scenes:
            db_scene = crud.create_scene(db, script_id, {
                "scene_number": scene.scene_number,
                "description": scene.description,
                "duration": scene.duration,
                "visual_elements": scene.visual_elements,  # Mô tả chi tiết cho việc tạo hình ảnh
                "background_music": scene.background_music,
                "voice_over": scene.voice_over
            })
        
        # Lấy script đã cập nhật
        updated_script = crud.get_script(db, script_id)
        return updated_script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scripts", response_model=List[VideoScript])
async def list_scripts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lấy danh sách các kịch bản video
    """
    try:
        return crud.get_scripts(db, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scripts/{script_id}", response_model=VideoScript)
async def get_script(script_id: str, db: Session = Depends(get_db)):
    """
    Lấy thông tin chi tiết của một kịch bản video
    """
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        return script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scripts/{script_id}/save", response_model=VideoScript)
async def save_script(
    script_id: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Lưu script với user_id của người dùng
    """
    try:
        # Kiểm tra script có tồn tại không
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        # Kiểm tra script đã có creator_id chưa
        if script.creator_id:
            raise HTTPException(status_code=400, detail="Script already has a creator")
        
        # Cập nhật creator_id cho script
        updated_script = crud.update_script(db, script_id, {"creator_id": user_id})
        
        # Cập nhật status thành completed
        updated_script = crud.update_script(db, script_id, {"status": ScriptStatus.COMPLETED.value})
        
        return updated_script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 