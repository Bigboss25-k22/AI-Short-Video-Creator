from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.image_generation_service import ImageGenerationService
from app.schemas.image import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    SceneImageCreate,
    UpdateSceneImageRequest,
)
from app.core.database import get_db
from app.crud.video_script import get_scene, get_script
from app.models.video_script import SceneImage, MediaStatus, ScriptStatus, Scene
from typing import List
import os
import tempfile
import shutil
from app import crud
from app.services.image_generation_service import image_generation_service

router = APIRouter()
image_service = ImageGenerationService()
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.image_generation_service import ImageGenerationService
from app.schemas.image import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    SceneImageCreate,
    UpdateSceneImageRequest,
)
from app.core.database import get_db
from app.crud.video_script import get_scene, get_script
from app.models.video_script import SceneImage, MediaStatus, ScriptStatus, Scene
from typing import List

router = APIRouter()
image_service = ImageGenerationService()


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest, db: Session = Depends(get_db)
):
    """Tạo hình ảnh từ mô tả scene và lưu vào database"""
    try:
        scene = get_scene(db, request.scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        scene.image_status = MediaStatus.PROCESSING
        db.commit()

        prompt = request.prompt or scene.visual_elements
        if not prompt:
            scene.image_status = MediaStatus.FAILED
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="No prompt provided and scene has no visual elements",
            )

        try:
            image_url = image_service.generate_image(prompt)
            if not image_url:
                scene.image_status = MediaStatus.FAILED
                db.commit()
                raise HTTPException(status_code=500, detail="Failed to generate image")

            scene_image = SceneImage(
                scene_id=request.scene_id,
                image_url=image_url,
                prompt=prompt,
                width=request.width,
                height=request.height,
                status=MediaStatus.COMPLETED,
            )
            db.add(scene_image)

            scene.image_status = MediaStatus.COMPLETED
            db.commit()
            db.refresh(scene_image)

            return scene_image
        except Exception as e:
            scene.image_status = MediaStatus.FAILED
            db.commit()
            raise e

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-for-script/{script_id}")
async def generate_images_for_script(script_id: str, db: Session = Depends(get_db)):
    """Tạo hình ảnh cho tất cả các scene trong script và trả về tất cả hình ảnh"""
    try:
        script = get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        scenes = script.scenes
        if not scenes:
            raise HTTPException(
                status_code=404, detail="No scenes found for this script"
            )

        generated_images = []
        for scene in scenes:
            if not scene.images:
                scene.image_status = MediaStatus.PROCESSING.value
                db.commit()

                prompt = scene.visual_elements
                if not prompt:
                    scene.image_status = MediaStatus.FAILED.value
                    db.commit()
                    continue

                try:
                    image_url = image_service.generate_image(prompt)
                    if not image_url:
                        scene.image_status = MediaStatus.FAILED.value
                        db.commit()
                        continue

                    scene_image = SceneImage(
                        scene_id=scene.id,
                        image_url=image_url,
                        prompt=prompt,
                        width=1024,
                        height=768,
                        status=MediaStatus.COMPLETED.value,
                    )
                    db.add(scene_image)

                    scene.image_status = MediaStatus.COMPLETED.value
                    generated_images.append(
                        {
                            "id": scene_image.id,
                            "scene_id": scene_image.scene_id,
                            "scene_number": scene.scene_number,
                            "image_url": scene_image.image_url,
                            "prompt": scene_image.prompt,
                            "status": scene_image.status,
                        }
                    )
                except Exception:
                    scene.image_status = MediaStatus.FAILED.value
                    db.commit()
                    continue
            else:
                for image in scene.images:
                    generated_images.append(
                        {
                            "id": image.id,
                            "scene_id": image.scene_id,
                            "scene_number": scene.scene_number,
                            "image_url": image.image_url,
                            "prompt": image.prompt,
                            "status": image.status,
                        }
                    )

        db.commit()

        all_completed = all(
            scene.image_status == MediaStatus.COMPLETED.value for scene in scenes
        )
        if all_completed:
            script.status = ScriptStatus.COMPLETED.value
        else:
            script.status = ScriptStatus.FAILED.value
        db.commit()

        return generated_images
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scene-images/{image_id}", response_model=ImageGenerationResponse)
async def update_scene_image(
    image_id: str, request: UpdateSceneImageRequest, db: Session = Depends(get_db)
):
    """Cập nhật thông tin của một SceneImage đã tồn tại và cập nhật visual_elements trong scene"""
    try:
        scene_image = db.query(SceneImage).filter(SceneImage.id == image_id).first()
        if not scene_image:
            raise HTTPException(status_code=404, detail="Scene image not found")

        scene = get_scene(db, scene_image.scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        script = get_script(db, scene.script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        scene.image_status = MediaStatus.PROCESSING.value
        script.status = ScriptStatus.PROCESSING.value
        db.commit()

        try:
            new_image_url = image_service.generate_image(request.prompt)
            if not new_image_url:
                scene.image_status = MediaStatus.FAILED.value
                script.status = ScriptStatus.FAILED.value
                db.commit()
                raise HTTPException(
                    status_code=500, detail="Failed to generate new image"
                )

            scene.visual_elements = request.prompt

            scene_image.prompt = request.prompt
            scene_image.image_url = new_image_url
            if request.width:
                scene_image.width = request.width
            if request.height:
                scene_image.height = request.height
            scene_image.status = MediaStatus.COMPLETED.value

            scene.image_status = MediaStatus.COMPLETED.value

            all_completed = all(
                scene.image_status == MediaStatus.COMPLETED.value
                for scene in script.scenes
            )
            if all_completed:
                script.status = ScriptStatus.COMPLETED.value
            else:
                script.status = ScriptStatus.FAILED.value

            db.commit()
            db.refresh(scene_image)

            return ImageGenerationResponse(
                id=scene_image.id,
                scene_id=scene_image.scene_id,
                image_url=scene_image.image_url,
                prompt=scene_image.prompt,
                width=scene_image.width,
                height=scene_image.height,
                status=scene_image.status,
                scene_number=scene.scene_number,
            )
        except Exception as e:
            scene.image_status = MediaStatus.FAILED.value
            script.status = ScriptStatus.FAILED.value
            db.commit()
            raise e

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{script_id}", response_model=List[ImageGenerationResponse])
async def get_script_images(script_id: str, db: Session = Depends(get_db)):
    """Lấy tất cả hình ảnh của một script"""
    try:
        script = get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        all_images = []
        for scene in script.scenes:
            for image in scene.images:
                image_response = ImageGenerationResponse(
                    id=image.id,
                    scene_id=image.scene_id,
                    image_url=image.image_url,
                    prompt=image.prompt,
                    width=image.width,
                    height=image.height,
                    status=image.status,
                    scene_number=scene.scene_number,
                )
                all_images.append(image_response)

        return all_images
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scene-images/{image_id}")
async def delete_scene_image(image_id: str, db: Session = Depends(get_db)):
    """Xóa một hình ảnh của scene"""
    try:
        scene_image = db.query(SceneImage).filter(SceneImage.id == image_id).first()
        if not scene_image:
            raise HTTPException(status_code=404, detail="Scene image not found")

        scene = get_scene(db, scene_image.scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        db.delete(scene_image)

        if not scene.images:
            scene.image_status = MediaStatus.PENDING.value

        db.commit()

        return {"message": "Scene image deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-images-for-script/{script_id}")
async def save_images_for_script(
    script_id: str, images: List[dict], db: Session = Depends(get_db)
):
    """Lưu hình ảnh cho script với các bước kiểm tra"""
    try:
        script = get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        saved_images = []
        for image_data in images:
            scene_id = image_data.get("scene_id")
            scene_number = image_data.get("scene_number")
            image_url = image_data.get("image_url")
            prompt = image_data.get("prompt")

            if not all([scene_id, scene_number, image_url, prompt]):
                continue

            scene = db.query(Scene).filter(Scene.id == scene_id).first()
            if not scene:
                continue

            existing_images = (
                db.query(SceneImage).filter(SceneImage.scene_id == scene_id).all()
            )

            if not existing_images:
                new_image = SceneImage(
                    scene_id=scene_id,
                    image_url=image_url,
                    prompt=prompt,
                    width=1024,
                    height=768,
                    status=MediaStatus.COMPLETED.value,
                )
                db.add(new_image)
                saved_images.append(
                    {
                        "id": new_image.id,
                        "scene_id": scene_id,
                        "scene_number": scene_number,
                        "image_url": image_url,
                        "prompt": prompt,
                        "status": MediaStatus.COMPLETED.value,
                        "action": "created",
                    }
                )
            else:
                is_duplicate = any(
                    img.image_url == image_url for img in existing_images
                )
                if not is_duplicate:
                    for old_image in existing_images:
                        db.delete(old_image)

                    new_image = SceneImage(
                        scene_id=scene_id,
                        image_url=image_url,
                        prompt=prompt,
                        width=1024,
                        height=768,
                        status=MediaStatus.COMPLETED.value,
                    )
                    db.add(new_image)
                    saved_images.append(
                        {
                            "id": new_image.id,
                            "scene_id": scene_id,
                            "scene_number": scene_number,
                            "image_url": image_url,
                            "prompt": prompt,
                            "status": MediaStatus.COMPLETED.value,
                            "action": "replaced",
                        }
                    )
                else:
                    saved_images.append(
                        {
                            "id": existing_images[0].id,
                            "scene_id": scene_id,
                            "scene_number": scene_number,
                            "image_url": image_url,
                            "prompt": prompt,
                            "status": MediaStatus.COMPLETED.value,
                            "action": "skipped",
                        }
                    )

        for scene in script.scenes:
            scene.image_status = MediaStatus.COMPLETED.value

        script.status = ScriptStatus.COMPLETED.value
        db.commit()

        return {
            "message": f"Successfully processed {len(saved_images)} images",
            "images": saved_images,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test")
async def test_image_api():
    """Endpoint test để kiểm tra API hoạt động"""
    return {"message": "Image API is working", "status": "ok"}
