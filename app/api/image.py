from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.image_generation_service import ImageGenerationService
from app.schemas.image import (
    ImageGenerationRequest, 
    ImageGenerationResponse, 
    SceneImageCreate,
    UpdateSceneImageRequest
)
from app.database import get_db
from app.crud.video_script import get_scene, get_script
from app.models.video_script import SceneImage, MediaStatus, ScriptStatus
from typing import List
import os
import tempfile
import shutil

router = APIRouter()
image_service = ImageGenerationService()

@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest, db: Session = Depends(get_db)):
    """
    Tạo hình ảnh từ mô tả scene và lưu vào database
    """
    try:
        # Kiểm tra scene có tồn tại không
        scene = get_scene(db, request.scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        # Cập nhật trạng thái scene thành processing
        scene.image_status = MediaStatus.PROCESSING
        db.commit()

        # Sử dụng visual_elements của scene nếu không có prompt
        prompt = request.prompt or scene.visual_elements
        if not prompt:
            scene.image_status = MediaStatus.FAILED
            db.commit()
            raise HTTPException(status_code=400, detail="No prompt provided and scene has no visual elements")

        try:
            # Tạo hình ảnh từ prompt
            image_url = image_service.generate_image(prompt)
            if not image_url:
                scene.image_status = MediaStatus.FAILED
                db.commit()
                raise HTTPException(status_code=500, detail="Failed to generate image")

            # Tạo bản ghi SceneImage mới
            scene_image = SceneImage(
                scene_id=request.scene_id,
                image_url=image_url,
                prompt=prompt,
                width=request.width,
                height=request.height,
                status=MediaStatus.COMPLETED
            )
            db.add(scene_image)
            
            # Cập nhật trạng thái scene thành completed
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

@router.post("/generate-for-script/{script_id}", response_model=List[ImageGenerationResponse])
async def generate_images_for_script(script_id: str, db: Session = Depends(get_db)):
    """
    Tạo hình ảnh cho tất cả các scenes trong một script
    """
    try:
        # Kiểm tra script có tồn tại không
        script = get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        # Cập nhật trạng thái script thành processing
        script.status = ScriptStatus.PROCESSING.value
        db.commit()

        generated_images = []
        
        # Duyệt qua từng scene trong script
        for scene in script.scenes:
            # Kiểm tra xem scene đã có hình ảnh chưa
            if not scene.images:
                # Cập nhật trạng thái scene thành processing
                scene.image_status = MediaStatus.PROCESSING.value
                db.commit()

                # Sử dụng visual_elements của scene làm prompt
                prompt = scene.visual_elements
                if not prompt:
                    scene.image_status = MediaStatus.FAILED.value
                    db.commit()
                    continue  # Bỏ qua scene không có visual_elements

                try:
                    # Tạo hình ảnh từ prompt
                    image_url = image_service.generate_image(prompt)
                    if not image_url:
                        scene.image_status = MediaStatus.FAILED.value
                        db.commit()
                        continue  # Bỏ qua nếu tạo hình ảnh thất bại

                    # Tạo bản ghi SceneImage mới
                    scene_image = SceneImage(
                        scene_id=scene.id,
                        image_url=image_url,
                        prompt=prompt,
                        width=1024,  # Giá trị mặc định
                        height=768,   # Giá trị mặc định
                        status=MediaStatus.COMPLETED.value
                    )
                    db.add(scene_image)
                    
                    # Cập nhật trạng thái scene thành completed
                    scene.image_status = MediaStatus.COMPLETED.value
                    generated_images.append(scene_image)
                except Exception as e:
                    scene.image_status = MediaStatus.FAILED.value
                    db.commit()
                    continue

        db.commit()
        
        # Kiểm tra xem tất cả scenes đã hoàn thành chưa
        all_completed = all(scene.image_status == MediaStatus.COMPLETED.value for scene in script.scenes)
        if all_completed:
            script.status = ScriptStatus.COMPLETED.value
        else:
            script.status = ScriptStatus.FAILED.value
        db.commit()
        
        # Refresh tất cả các scene_image để lấy thông tin đầy đủ
        for image in generated_images:
            db.refresh(image)

        return generated_images

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/scene-images/{image_id}", response_model=ImageGenerationResponse)
async def update_scene_image(
    image_id: str,
    request: UpdateSceneImageRequest,
    db: Session = Depends(get_db)
):
    """
    Cập nhật thông tin của một SceneImage đã tồn tại và cập nhật visual_elements trong scene
    """
    try:
        # Lấy SceneImage từ database
        scene_image = db.query(SceneImage).filter(SceneImage.id == image_id).first()
        if not scene_image:
            raise HTTPException(status_code=404, detail="Scene image not found")

        # Lấy scene tương ứng
        scene = get_scene(db, scene_image.scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        # Lấy script tương ứng
        script = get_script(db, scene.script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        # Cập nhật trạng thái scene và script thành processing
        scene.image_status = MediaStatus.PROCESSING.value
        script.status = ScriptStatus.PROCESSING.value
        db.commit()

        try:
            # Tạo hình ảnh mới từ prompt mới
            new_image_url = image_service.generate_image(request.prompt)
            if not new_image_url:
                scene.image_status = MediaStatus.FAILED.value
                script.status = ScriptStatus.FAILED.value
                db.commit()
                raise HTTPException(status_code=500, detail="Failed to generate new image")

            # Cập nhật visual_elements trong scene
            scene.visual_elements = request.prompt

            # Cập nhật thông tin SceneImage
            scene_image.prompt = request.prompt
            scene_image.image_url = new_image_url
            if request.width:
                scene_image.width = request.width
            if request.height:
                scene_image.height = request.height
            scene_image.status = MediaStatus.COMPLETED.value
            
            # Cập nhật trạng thái scene thành completed
            scene.image_status = MediaStatus.COMPLETED.value

            # Kiểm tra xem tất cả scenes đã hoàn thành chưa
            all_completed = all(scene.image_status == MediaStatus.COMPLETED.value for scene in script.scenes)
            if all_completed:
                script.status = ScriptStatus.COMPLETED.value
            else:
                script.status = ScriptStatus.FAILED.value

            db.commit()
            db.refresh(scene_image)

            return scene_image
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
    """
    Lấy tất cả hình ảnh của một script
    """
    try:
        # Kiểm tra script có tồn tại không
        script = get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        # Lấy tất cả hình ảnh của các scene trong script
        all_images = []
        for scene in script.scenes:
            for image in scene.images:
                # Tạo response với scene_number
                image_response = ImageGenerationResponse(
                    id=image.id,
                    scene_id=image.scene_id,
                    image_url=image.image_url,
                    prompt=image.prompt,
                    width=image.width,
                    height=image.height,
                    status=image.status,
                    scene_number=scene.scene_number
                )
                all_images.append(image_response)

        return all_images
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 