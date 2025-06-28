from fastapi import APIRouter, HTTPException, Depends, Response, Request
from sqlalchemy.orm import Session
from app.schemas.video_script import VideoScript, CreateScriptRequest, VideoScript as VideoScriptSchema
from app.services.deepseek_service import DeepSeekService
from app.crud import video_script as crud
from app.core.database import get_db
from app.models.video_script import ScriptStatus, MediaStatus
from typing import Optional, List
import os
import tempfile
import shutil
from pydantic import BaseModel
from app.models.user import User
from app.middleware.auth import require_auth

router = APIRouter()
deepseek_service = DeepSeekService()

class TextToSpeechRequest(BaseModel):
    text: str
    voice_id: str = "vi-VN-Wavenet-A"  # Vietnamese female voice
    speed: float = 1.0

class UpdateVideoUrlRequest(BaseModel):
    video_url: str

@router.post("/generate", response_model=VideoScript)
async def generate_video_script(
    create_request: CreateScriptRequest, 
    db: Session = Depends(get_db)
):
    """
    Tạo kịch bản video tự động dựa trên chủ đề, đối tượng mục tiêu và thời lượng
    """
    db_script = None  # Khởi tạo biến db_script
    try:
        # Tạo nội dung script bằng DeepSeek
        script = deepseek_service.generate_video_script(
            topic=create_request.topic,
            target_audience=create_request.target_audience,
            duration=create_request.duration
        )
        
        # Tạo script trong database với status DRAFT và creator_id = null
        db_script = crud.create_script(db, create_request)
        
        # Cập nhật thông tin script trong database (creator_id sẽ là null)
        crud.update_script(db, db_script.id, {
            "title": script.title,
            "description": script.description,
            "total_duration": script.total_duration,
            "creator_id": None,  # Để null, sẽ được cập nhật khi user lưu
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
        # Chuyển sang schema Pydantic để loại bỏ InstanceState
        script_schema = VideoScriptSchema.model_validate(db_script)
        # Cải thiện script bằng DeepSeek
        enhanced_script = deepseek_service.enhance_script(script_schema)
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
@require_auth()
async def save_script(
    request: Request,
    script_id: str,
    db: Session = Depends(get_db)
):
    """
    Lưu script với user_id của người dùng hiện tại
    """
    try:
        # Kiểm tra script có tồn tại không
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        # Kiểm tra script đã có creator_id chưa
        if script.creator_id:
            raise HTTPException(status_code=400, detail="Script already has a creator")
        
        # Lấy user từ accessToken
        username = request.state.user["sub"]
        user = db.query(User).filter_by(username=username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user.id
        
        # Cập nhật creator_id cho script
        updated_script = crud.update_script(db, script_id, {"creator_id": user_id})
        # Cập nhật status thành completed
        updated_script = crud.update_script(db, script_id, {"status": ScriptStatus.COMPLETED.value})
        return updated_script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/scripts/{script_id}")
async def delete_script(script_id: str, db: Session = Depends(get_db)):
    """
    Xóa một kịch bản video và tất cả tài nguyên liên quan
    """
    try:
        # Lấy script từ database
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        # Xóa tất cả các scene và tài nguyên liên quan
        for scene in script.scenes:
            # Xóa tất cả hình ảnh của scene
            for image in scene.images:
                db.delete(image)
            
            # Xóa tất cả voice audio của scene
            for voice in scene.voice_audios:
                db.delete(voice)
            
            # Xóa scene
            db.delete(scene)
        
        # Xóa script
        db.delete(script)
        db.commit()

        return {"message": "Script and all related resources deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/scenes/{scene_id}")
async def delete_scene(scene_id: str, db: Session = Depends(get_db)):
    """
    Xóa một scene và tất cả tài nguyên liên quan
    """
    try:
        # Lấy scene từ database
        scene = crud.get_scene(db, scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        # Xóa tất cả hình ảnh của scene
        for image in scene.images:
            db.delete(image)
        
        # Xóa tất cả voice audio của scene
        for voice in scene.voice_audios:
            db.delete(voice)
        
        # Xóa scene
        db.delete(scene)
        db.commit()

        return {"message": "Scene and all related resources deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/scripts/{script_id}/video-url", response_model=VideoScript)
@require_auth()
async def update_video_url(
    request: Request,
    script_id: str,
    video_url_request: UpdateVideoUrlRequest,
    db: Session = Depends(get_db)
):
    """
    Cập nhật video URL cho script sau khi upload lên cloud storage
    """
    try:
        # Kiểm tra script có tồn tại không
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        # Lấy user từ accessToken để kiểm tra quyền
        username = request.state.user["sub"]
        user = db.query(User).filter_by(username=username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Kiểm tra xem user có quyền cập nhật script này không
        if script.creator_id and script.creator_id != user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to update this script")
        
        # Cập nhật video URL
        updated_script = crud.update_script(db, script_id, {
            "video_url": video_url_request.video_url,
            "status": ScriptStatus.COMPLETED.value  # Cập nhật status thành completed khi có video
        })
        
        return updated_script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 