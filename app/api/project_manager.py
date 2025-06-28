from fastapi import APIRouter, HTTPException, Depends, Response, Request
from sqlalchemy.orm import Session
from app.schemas.video_script import VideoScript, CreateScriptRequest, Scene
from app.crud import video_script as crud
from app.core.database import get_db
from app.models.video_script import ScriptStatus
from app.models.user import User
from typing import Optional, List
from pydantic import BaseModel
from app.middleware.auth import require_auth

router = APIRouter()

class ScriptUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[str] = None
    total_duration: Optional[int] = None
    video_url: Optional[str] = None
    status: Optional[ScriptStatus] = None

class SceneUpdateRequest(BaseModel):
    scene_number: int
    description: str
    duration: int
    visual_elements: str
    background_music: Optional[str] = None
    voice_over: Optional[str] = None

class ScriptScenesUpdateRequest(BaseModel):
    scenes: List[SceneUpdateRequest]

@router.get("/user/scripts", response_model=List[VideoScript])
@require_auth()
async def get_user_scripts(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status: Optional[ScriptStatus] = None,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách kịch bản video của user hiện tại
    """
    try:
        username = request.state.user["sub"]
        user = db.query(User).filter_by(username=username).first()
        scripts = crud.get_scripts_by_user(db, user.id, skip=skip, limit=limit, status=status)
        return scripts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scripts/{script_id}", response_model=VideoScript)
@require_auth()
async def get_script(
    request: Request,
    script_id: str,
    db: Session = Depends(get_db)
):
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

@router.put("/scripts/{script_id}", response_model=VideoScript)
@require_auth()
async def update_script(
    request: Request,
    script_id: str,
    update_data: ScriptUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Cập nhật thông tin kịch bản video
    """
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        updated_script = crud.update_script(db, script_id, update_dict)
        return updated_script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/scripts/{script_id}")
@require_auth()
async def delete_script(
    request: Request,
    script_id: str,
    db: Session = Depends(get_db)
):
    """
    Xóa một kịch bản video
    """
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
            
        success = crud.delete_script(db, script_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete script")
        return {"message": "Script deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scripts/{script_id}/archive")
@require_auth()
async def archive_script(
    request: Request,
    script_id: str,
    db: Session = Depends(get_db)
):
    """
    Lưu trữ một kịch bản video (chuyển trạng thái sang ARCHIVED)
    """
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
            
        updated_script = crud.update_script(db, script_id, {"status": ScriptStatus.ARCHIVED})
        return {"message": "Script archived successfully", "script": updated_script}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scripts/{script_id}/restore")
@require_auth()
async def restore_script(
    request: Request,
    script_id: str,
    db: Session = Depends(get_db)
):
    """
    Khôi phục một kịch bản video từ trạng thái ARCHIVED về ACTIVE
    """
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        if script.status != ScriptStatus.ARCHIVED:
            raise HTTPException(status_code=400, detail="Script is not archived")

        updated_script = crud.update_script(db, script_id, {"status": ScriptStatus.ACTIVE})
        return {"message": "Script restored successfully", "script": updated_script}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/scripts/{script_id}/scenes", response_model=VideoScript)
@require_auth()
async def update_script_scenes(
    request: Request,
    script_id: str,
    update_data: ScriptScenesUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Cập nhật scenes của kịch bản video
    """
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        # Xóa tất cả scenes hiện tại
        for scene in script.scenes:
            db.delete(scene)
        db.commit()

        # Tạo scenes mới
        for scene_data in update_data.scenes:
            crud.create_scene(db, script_id, {
                "scene_number": scene_data.scene_number,
                "description": scene_data.description,
                "duration": scene_data.duration,
                "visual_elements": scene_data.visual_elements,
                "background_music": scene_data.background_music,
                "voice_over": scene_data.voice_over
            })

        # Lấy script đã cập nhật
        updated_script = crud.get_script(db, script_id)
        return updated_script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 