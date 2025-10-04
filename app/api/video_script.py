from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.schemas.video_script import (
    VideoScript,
    CreateScriptRequest,
    VideoScript as VideoScriptSchema,
)
from app.services.deepseek_service import DeepSeekService
from app.crud import video_script as crud
from app.core.database import get_db
from app.models.video_script import ScriptStatus, MediaStatus
from typing import List
import os
import tempfile
from pydantic import BaseModel
from app.models.user import User
from app.middleware.auth import require_auth
import requests

router = APIRouter()
deepseek_service = DeepSeekService()


class TextToSpeechRequest(BaseModel):
    text: str
    voice_id: str = "vi-VN-Wavenet-A"
    speed: float = 1.0


class UpdateVideoUrlRequest(BaseModel):
    video_url: str


@router.post("/generate", response_model=VideoScript)
@require_auth()
async def generate_video_script(
    request: Request, create_request: CreateScriptRequest, db: Session = Depends(get_db)
):
    """Tạo kịch bản video tự động dựa trên chủ đề, đối tượng mục tiêu và thời lượng"""
    db_script = None
    try:
        username = request.state.user["sub"]
        user = db.query(User).filter_by(username=username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user.id

        script = deepseek_service.generate_video_script(
            topic=create_request.topic,
            target_audience=create_request.target_audience,
            duration=create_request.duration,
        )

        db_script = crud.create_script(db, create_request, creator_id=user_id)

        crud.update_script(
            db,
            db_script.id,
            {
                "title": script.title,
                "description": script.description,
                "total_duration": script.total_duration,
                "creator_id": user_id,
                "status": ScriptStatus.DRAFT.value,
            },
        )

        for scene in script.scenes:
            crud.create_scene(
                db,
                db_script.id,
                {
                    "scene_number": scene.scene_number,
                    "description": scene.description,
                    "duration": scene.duration,
                    "visual_elements": scene.visual_elements,
                    "background_music": scene.background_music,
                    "voice_over": scene.voice_over,
                    "image_status": MediaStatus.PENDING.value,
                    "voice_status": MediaStatus.PENDING.value,
                },
            )

        saved_script = crud.get_script(db, db_script.id)
        return saved_script
    except Exception as e:
        if db_script:
            crud.update_script(db, db_script.id, {"status": ScriptStatus.FAILED.value})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enhance/{script_id}", response_model=VideoScript)
async def enhance_video_script(script_id: str, db: Session = Depends(get_db)):
    """Cải thiện kịch bản video với các đề xuất chi tiết hơn"""
    try:
        db_script = crud.get_script(db, script_id)
        if not db_script:
            raise HTTPException(status_code=404, detail="Script not found")

        script_schema = VideoScriptSchema.model_validate(db_script)
        enhanced_script = deepseek_service.enhance_script(script_schema)

        crud.update_script(
            db,
            script_id,
            {
                "title": enhanced_script.title,
                "description": enhanced_script.description,
                "total_duration": enhanced_script.total_duration,
            },
        )

        for scene in db_script.scenes:
            db.delete(scene)
        db.commit()

        for scene in enhanced_script.scenes:
            crud.create_scene(
                db,
                script_id,
                {
                    "scene_number": scene.scene_number,
                    "description": scene.description,
                    "duration": scene.duration,
                    "visual_elements": scene.visual_elements,
                    "background_music": scene.background_music,
                    "voice_over": scene.voice_over,
                },
            )

        updated_script = crud.get_script(db, script_id)
        return updated_script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scripts", response_model=List[VideoScript])
async def list_scripts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Lấy danh sách các kịch bản video (không signed URL)"""
    try:
        return crud.get_scripts(db, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scripts/{script_id}", response_model=VideoScript)
async def get_script(script_id: str, db: Session = Depends(get_db)):
    """Lấy thông tin chi tiết của một kịch bản video (không signed URL)"""
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        return script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scripts/{script_id}/save", response_model=VideoScript)
@require_auth()
async def save_script(request: Request, script_id: str, db: Session = Depends(get_db)):
    """Lưu script với user_id của người dùng hiện tại và upload ảnh lên cloud storage"""
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        if script.creator_id:
            raise HTTPException(status_code=400, detail="Script already has a creator")

        username = request.state.user["sub"]
        user = db.query(User).filter_by(username=username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user.id

        cover_image_url = None

        for scene in script.scenes:
            for scene_image in scene.images:
                if not scene_image.image_url:
                    continue

                if scene_image.image_url.startswith("https://storage.googleapis.com/"):
                    if cover_image_url is None:
                        cover_image_url = scene_image.image_url
                    continue

                if scene_image.image_url.startswith("http"):
                    try:
                        response = requests.get(scene_image.image_url, timeout=30)
                        response.raise_for_status()

                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=".jpg"
                        ) as temp_file:
                            temp_file.write(response.content)
                            temp_file_path = temp_file.name

                        try:
                            with open(temp_file_path, "rb") as image_file:
                                import uuid

                                unique_filename = (
                                    f"script-images/{script_id}/{uuid.uuid4()}.jpg"
                                )

                                from app.api.storage import upload_image_to_cloud

                                cloud_url = await upload_image_to_cloud(
                                    image_file, unique_filename
                                )

                                scene_image.image_url = cloud_url
                                db.commit()

                                if cover_image_url is None:
                                    cover_image_url = cloud_url
                        finally:
                            if os.path.exists(temp_file_path):
                                os.unlink(temp_file_path)
                    except Exception:
                        continue

                elif os.path.exists(scene_image.image_url):
                    try:
                        with open(scene_image.image_url, "rb") as image_file:
                            import uuid

                            file_extension = os.path.splitext(scene_image.image_url)[1]
                            unique_filename = f"script-images/{script_id}/{uuid.uuid4()}{file_extension}"

                            from app.api.storage import upload_image_to_cloud

                            cloud_url = await upload_image_to_cloud(
                                image_file, unique_filename
                            )

                            scene_image.image_url = cloud_url
                            db.commit()

                            if cover_image_url is None:
                                cover_image_url = cloud_url
                    except Exception:
                        continue

        update_data = {"creator_id": user_id, "status": ScriptStatus.COMPLETED.value}

        if cover_image_url:
            update_data["cover_image"] = cover_image_url

        updated_script = crud.update_script(db, script_id, update_data)
        return updated_script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scripts/{script_id}")
async def delete_script(script_id: str, db: Session = Depends(get_db)):
    """Xóa một kịch bản video và tất cả tài nguyên liên quan"""
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        for scene in script.scenes:
            for image in scene.images:
                db.delete(image)

            for voice in scene.voice_audios:
                db.delete(voice)

            db.delete(scene)

        db.delete(script)
        db.commit()

        return {"message": "Script and all related resources deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scenes/{scene_id}")
async def delete_scene(scene_id: str, db: Session = Depends(get_db)):
    """Xóa một scene và tất cả tài nguyên liên quan"""
    try:
        scene = crud.get_scene(db, scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        for image in scene.images:
            db.delete(image)

        for voice in scene.voice_audios:
            db.delete(voice)

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
    db: Session = Depends(get_db),
):
    """Cập nhật video URL cho script sau khi upload lên cloud storage"""
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        username = request.state.user["sub"]
        user = db.query(User).filter_by(username=username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if script.creator_id and script.creator_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to update this script",
            )

        updated_script = crud.update_script(
            db,
            script_id,
            {
                "video_url": video_url_request.video_url,
                "status": ScriptStatus.COMPLETED.value,
            },
        )

        return updated_script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scripts/{script_id}/upload-images-from-urls", response_model=VideoScript)
@require_auth()
async def upload_images_from_urls(
    request: Request, script_id: str, db: Session = Depends(get_db)
):
    """Upload tất cả ảnh từ URL (Replicate) lên Google Cloud Storage và cập nhật cover_image"""
    try:
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        username = request.state.user["sub"]
        user = db.query(User).filter_by(username=username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if script.creator_id and script.creator_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to update this script",
            )

        cover_image_url = None

        for scene in script.scenes:
            for scene_image in scene.images:
                if not scene_image.image_url:
                    continue

                if scene_image.image_url.startswith("https://storage.googleapis.com/"):
                    if cover_image_url is None:
                        cover_image_url = scene_image.image_url
                    continue

                if scene_image.image_url.startswith("http"):
                    try:
                        response = requests.get(scene_image.image_url, timeout=30)
                        response.raise_for_status()

                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=".jpg"
                        ) as temp_file:
                            temp_file.write(response.content)
                            temp_file_path = temp_file.name

                        try:
                            with open(temp_file_path, "rb") as image_file:
                                import uuid

                                unique_filename = (
                                    f"script-images/{script_id}/{uuid.uuid4()}.jpg"
                                )

                                from app.api.storage import upload_image_to_cloud

                                cloud_url = await upload_image_to_cloud(
                                    image_file, unique_filename
                                )

                                scene_image.image_url = cloud_url
                                db.commit()

                                if cover_image_url is None:
                                    cover_image_url = cloud_url
                        finally:
                            if os.path.exists(temp_file_path):
                                os.unlink(temp_file_path)
                    except Exception:
                        continue

        update_data = {}
        if cover_image_url:
            update_data["cover_image"] = cover_image_url

        if update_data:
            updated_script = crud.update_script(db, script_id, update_data)
            return updated_script

        return script
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
