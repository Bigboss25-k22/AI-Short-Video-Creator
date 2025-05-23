from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.image_generation_service import ImageGenerationService
from app.schemas.image import ImageGenerationRequest, ImageGenerationResponse
from app.database import get_db
from app.crud import video_script as crud
from app.models.video_script import SceneImage
import uuid

router = APIRouter()
image_service = ImageGenerationService()

@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest, db: Session = Depends(get_db)):
    """
    Tạo hình ảnh từ mô tả scene và lưu vào database
    """
    try:
        # Kiểm tra scene có tồn tại không
        scene = crud.get_scene(db, request.scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        # Tạo hình ảnh từ visual_elements của scene
        image_url = image_service.generate_image(
            prompt=scene.visual_elements,
            width=request.width,
            height=request.height
        )
        if not image_url:
            raise HTTPException(status_code=500, detail="Failed to generate image")

        # Tạo bản ghi SceneImage mới
        scene_image = SceneImage(
            id=str(uuid.uuid4()),
            scene_id=request.scene_id,
            image_url=image_url,
            prompt=scene.visual_elements,
            width=request.width,
            height=request.height
        )
        db.add(scene_image)
        db.commit()
        db.refresh(scene_image)

        return ImageGenerationResponse(
            id=scene_image.id,
            scene_id=scene_image.scene_id,
            image_url=scene_image.image_url,
            prompt=scene_image.prompt,
            width=scene_image.width,
            height=scene_image.height,
            created_at=scene_image.created_at
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-all/{script_id}")
async def generate_all_images(script_id: str, db: Session = Depends(get_db)):
    """
    Tạo hình ảnh cho tất cả các scene trong script
    """
    try:
        # Lấy script từ database
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        generated_images = []
        # Tạo hình ảnh cho từng scene
        for scene in script.scenes:
            if not scene.visual_elements:
                continue

            # Tạo hình ảnh từ visual_elements
            image_url = image_service.generate_image(
                prompt=scene.visual_elements,
                width=1024,
                height=768
            )
            if not image_url:
                continue

            # Lưu thông tin hình ảnh vào database
            scene_image = SceneImage(
                id=str(uuid.uuid4()),
                scene_id=scene.id,
                image_url=image_url,
                prompt=scene.visual_elements,
                width=1024,
                height=768
            )
            db.add(scene_image)
            generated_images.append(scene_image)

        db.commit()
        return {"message": f"Generated {len(generated_images)} images successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 