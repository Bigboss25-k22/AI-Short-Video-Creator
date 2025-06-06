from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from app.schemas.video_script import VideoScript, CreateScriptRequest
from app.crud import video_script as crud
from app.database import get_db
from app.models.video_script import ScriptStatus
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter()

class ScriptUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[str] = None
    status: Optional[ScriptStatus] = None

@router.get("/user/{user_id}/scripts", response_model=List[VideoScript])
async def get_user_scripts(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[ScriptStatus] = None,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách kịch bản video của một người dùng
    """
    try:
        scripts = crud.get_scripts_by_user(db, user_id, skip=skip, limit=limit, status=status)
        return scripts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scripts/{script_id}", response_model=VideoScript)
async def get_script(
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
async def update_script(
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
        
        # Chuyển đổi Pydantic model thành dict và loại bỏ các giá trị None
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        updated_script = crud.update_script(db, script_id, update_dict)
        return updated_script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/scripts/{script_id}")
async def delete_script(
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
async def archive_script(
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
async def restore_script(
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