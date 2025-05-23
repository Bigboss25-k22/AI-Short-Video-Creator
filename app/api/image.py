from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.image_generation_service import ImageGenerationService
from app.schemas.image import ImageGenerationRequest, ImageGenerationResponse, SceneImageCreate
from app.database import get_db
from app.crud.video_script import get_scene
from app.models.video_script import SceneImage

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