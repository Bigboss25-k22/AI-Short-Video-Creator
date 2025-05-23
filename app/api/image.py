from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.image_generation_service import ImageGenerationService
from app.schemas.image import ImageGenerationRequest, ImageGenerationResponse, SceneImageCreate
from app.database import get_db
from app.crud.video_script import get_scene, get_script
from app.models.video_script import SceneImage
from typing import List

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

        # Sử dụng visual_elements của scene nếu không có prompt
        prompt = request.prompt or scene.visual_elements
        if not prompt:
            raise HTTPException(status_code=400, detail="No prompt provided and scene has no visual elements")

        # Tạo hình ảnh từ prompt
        image_url = image_service.generate_image(prompt)
        if not image_url:
            raise HTTPException(status_code=500, detail="Failed to generate image")

        # Tạo bản ghi SceneImage mới
        scene_image = SceneImage(
            scene_id=request.scene_id,
            image_url=image_url,
            prompt=prompt,
            width=request.width,
            height=request.height
        )
        db.add(scene_image)
        db.commit()
        db.refresh(scene_image)

        return scene_image
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

        generated_images = []
        
        # Duyệt qua từng scene trong script
        for scene in script.scenes:
            # Kiểm tra xem scene đã có hình ảnh chưa
            if not scene.images:
                # Sử dụng visual_elements của scene làm prompt
                prompt = scene.visual_elements
                if not prompt:
                    continue  # Bỏ qua scene không có visual_elements

                # Tạo hình ảnh từ prompt
                image_url = image_service.generate_image(prompt)
                if not image_url:
                    continue  # Bỏ qua nếu tạo hình ảnh thất bại

                # Tạo bản ghi SceneImage mới
                scene_image = SceneImage(
                    scene_id=scene.id,
                    image_url=image_url,
                    prompt=prompt,
                    width=1024,  # Giá trị mặc định
                    height=768   # Giá trị mặc định
                )
                db.add(scene_image)
                generated_images.append(scene_image)

        db.commit()
        
        # Refresh tất cả các scene_image để lấy thông tin đầy đủ
        for image in generated_images:
            db.refresh(image)

        return generated_images

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 