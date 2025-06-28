from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.image_generation_service import ImageGenerationService
from app.schemas.image import (
    ImageGenerationRequest, 
    ImageGenerationResponse, 
    SceneImageCreate,
    UpdateSceneImageRequest
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

@router.post("/generate-for-script/{script_id}")
async def generate_images_for_script(
    script_id: str,
    db: Session = Depends(get_db)
):
    """
    Tạo hình ảnh cho tất cả các scene trong script và trả về tất cả hình ảnh
    """
    try:
        # Lấy script từ database
        script = get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        print(f"Found script: {script.id}")

        # Lấy tất cả scenes của script
        scenes = script.scenes  # Sử dụng relationship trực tiếp
        if not scenes:
            raise HTTPException(status_code=404, detail="No scenes found for this script")
        
        print(f"Found {len(scenes)} scenes")

        # Tạo hình ảnh cho từng scene
        generated_images = []
        for scene in scenes:
            print(f"Processing scene {scene.scene_number}")
            
            # Kiểm tra xem scene đã có hình ảnh chưa
            if not scene.images:
                print(f"Scene {scene.scene_number} has no images, generating...")
                
                # Cập nhật trạng thái scene thành processing
                scene.image_status = MediaStatus.PROCESSING.value
                db.commit()

                # Sử dụng visual_elements của scene làm prompt
                prompt = scene.visual_elements
                if not prompt:
                    print(f"Scene {scene.scene_number} has no visual_elements")
                    scene.image_status = MediaStatus.FAILED.value
                    db.commit()
                    continue  # Bỏ qua scene không có visual_elements

                try:
                    print(f"Generating image for scene {scene.scene_number} with prompt: {prompt}")
                    # Tạo hình ảnh từ prompt
                    image_url = image_service.generate_image(prompt)
                    if not image_url:
                        print(f"Failed to generate image for scene {scene.scene_number}")
                        scene.image_status = MediaStatus.FAILED.value
                        db.commit()
                        continue  # Bỏ qua nếu tạo hình ảnh thất bại

                    print(f"Successfully generated image for scene {scene.scene_number}")
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
                    generated_images.append({
                        "id": scene_image.id,
                        "scene_id": scene_image.scene_id,
                        "scene_number": scene.scene_number,
                        "image_url": scene_image.image_url,
                        "prompt": scene_image.prompt,
                        "status": scene_image.status
                    })
                except Exception as e:
                    print(f"Error generating image for scene {scene.scene_number}: {str(e)}")
                    scene.image_status = MediaStatus.FAILED.value
                    db.commit()
                    continue
            else:
                print(f"Scene {scene.scene_number} already has images")
                # Thêm tất cả hình ảnh hiện có của scene vào kết quả
                for image in scene.images:
                    generated_images.append({
                        "id": image.id,
                        "scene_id": image.scene_id,
                        "scene_number": scene.scene_number,
                        "image_url": image.image_url,
                        "prompt": image.prompt,
                        "status": image.status
                    })

        db.commit()
        
        # Kiểm tra xem tất cả scenes đã hoàn thành chưa
        all_completed = all(scene.image_status == MediaStatus.COMPLETED.value for scene in scenes)
        if all_completed:
            script.status = ScriptStatus.COMPLETED.value
        else:
            script.status = ScriptStatus.FAILED.value
        db.commit()

        print(f"Returning {len(generated_images)} images")
        return generated_images
    except Exception as e:
        print(f"Error in generate_images_for_script: {str(e)}")
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
        print(f"Updating scene image with ID: {image_id}")
        print(f"Request data: {request}")
        
        # Lấy SceneImage từ database
        scene_image = db.query(SceneImage).filter(SceneImage.id == image_id).first()
        if not scene_image:
            print(f"Scene image not found with ID: {image_id}")
            raise HTTPException(status_code=404, detail="Scene image not found")

        print(f"Found scene image: {scene_image.id}")

        # Lấy scene tương ứng
        scene = get_scene(db, scene_image.scene_id)
        if not scene:
            print(f"Scene not found with ID: {scene_image.scene_id}")
            raise HTTPException(status_code=404, detail="Scene not found")

        print(f"Found scene: {scene.id}, scene_number: {scene.scene_number}")

        # Lấy script tương ứng
        script = get_script(db, scene.script_id)
        if not script:
            print(f"Script not found with ID: {scene.script_id}")
            raise HTTPException(status_code=404, detail="Script not found")

        print(f"Found script: {script.id}")
        # Cập nhật trạng thái scene và script thành processing
        scene.image_status = MediaStatus.PROCESSING.value
        script.status = ScriptStatus.PROCESSING.value
        db.commit()

        try:
            print(f"Generating new image with prompt: {request.prompt}")
            # Tạo hình ảnh mới từ prompt mới
            new_image_url = image_service.generate_image(request.prompt)
            if not new_image_url:
                print("Failed to generate new image")
                scene.image_status = MediaStatus.FAILED.value
                script.status = ScriptStatus.FAILED.value
                db.commit()
                raise HTTPException(status_code=500, detail="Failed to generate new image")

            print(f"Successfully generated new image: {new_image_url}")

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

            print(f"Successfully updated scene image. Returning response with scene_number: {scene.scene_number}")

            # Trả về response với scene_number
            return ImageGenerationResponse(
                id=scene_image.id,
                scene_id=scene_image.scene_id,
                image_url=scene_image.image_url,
                prompt=scene_image.prompt,
                width=scene_image.width,
                height=scene_image.height,
                status=scene_image.status,
                scene_number=scene.scene_number
            )
        except Exception as e:
            print(f"Error during image generation: {str(e)}")
            scene.image_status = MediaStatus.FAILED.value
            script.status = ScriptStatus.FAILED.value
            db.commit()
            raise e

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

@router.delete("/scene-images/{image_id}")
async def delete_scene_image(image_id: str, db: Session = Depends(get_db)):
    """
    Xóa một hình ảnh của scene
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

        # Xóa hình ảnh
        db.delete(scene_image)
        
        # Cập nhật trạng thái scene nếu không còn hình ảnh nào
        if not scene.images:
            scene.image_status = MediaStatus.PENDING.value
        
        db.commit()

        return {"message": "Scene image deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-images-for-script/{script_id}")
async def save_images_for_script(
    script_id: str,
    images: List[dict],
    db: Session = Depends(get_db)
):
    """
    Lưu hình ảnh cho script với các bước kiểm tra:
    1. Kiểm tra script tồn tại
    2. Kiểm tra scene tồn tại
    3. Kiểm tra hình ảnh đã tồn tại chưa
    4. Nếu chưa tồn tại -> lưu mới
    5. Nếu đã tồn tại -> kiểm tra trùng lặp
    6. Nếu không trùng -> thay thế
    7. Nếu trùng -> bỏ qua
    """
    try:
        # Kiểm tra script tồn tại
        script = get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        print(f"Found script: {script.id}")
        
        saved_images = []
        for image_data in images:
            scene_id = image_data.get("scene_id")
            scene_number = image_data.get("scene_number")
            image_url = image_data.get("image_url")
            prompt = image_data.get("prompt")
            
            if not all([scene_id, scene_number, image_url, prompt]):
                print(f"Skipping invalid image data: {image_data}")
                continue
                
            # Kiểm tra scene tồn tại
            scene = db.query(Scene).filter(Scene.id == scene_id).first()
            if not scene:
                print(f"Scene {scene_id} not found, skipping")
                continue
                
            # Kiểm tra hình ảnh đã tồn tại chưa
            existing_images = db.query(SceneImage).filter(SceneImage.scene_id == scene_id).all()
            
            if not existing_images:
                # Chưa có hình ảnh -> lưu mới
                print(f"Creating new image for scene {scene_number}")
                new_image = SceneImage(
                    scene_id=scene_id,
                    image_url=image_url,
                    prompt=prompt,
                    width=1024,
                    height=768,
                    status=MediaStatus.COMPLETED.value
                )
                db.add(new_image)
                saved_images.append({
                    "id": new_image.id,
                    "scene_id": scene_id,
                    "scene_number": scene_number,
                    "image_url": image_url,
                    "prompt": prompt,
                    "status": MediaStatus.COMPLETED.value,
                    "action": "created"
                })
            else:
                # Đã có hình ảnh -> kiểm tra trùng lặp
                is_duplicate = any(img.image_url == image_url for img in existing_images)
                if not is_duplicate:
                    # Không trùng -> thay thế
                    print(f"Replacing existing images for scene {scene_number}")
                    # Xóa hình ảnh cũ
                    for old_image in existing_images:
                        db.delete(old_image)
                    
                    # Tạo hình ảnh mới
                    new_image = SceneImage(
                        scene_id=scene_id,
                        image_url=image_url,
                        prompt=prompt,
                        width=1024,
                        height=768,
                        status=MediaStatus.COMPLETED.value
                    )
                    db.add(new_image)
                    saved_images.append({
                        "id": new_image.id,
                        "scene_id": scene_id,
                        "scene_number": scene_number,
                        "image_url": image_url,
                        "prompt": prompt,
                        "status": MediaStatus.COMPLETED.value,
                        "action": "replaced"
                    })
                else:
                    # Trùng -> bỏ qua
                    print(f"Skipping duplicate image for scene {scene_number}")
                    saved_images.append({
                        "id": existing_images[0].id,
                        "scene_id": scene_id,
                        "scene_number": scene_number,
                        "image_url": image_url,
                        "prompt": prompt,
                        "status": MediaStatus.COMPLETED.value,
                        "action": "skipped"
                    })
        
        # Cập nhật trạng thái của scenes và script
        for scene in script.scenes:
            scene.image_status = MediaStatus.COMPLETED.value
        
        script.status = ScriptStatus.COMPLETED.value
        db.commit()
        
        return {
            "message": f"Successfully processed {len(saved_images)} images",
            "images": saved_images
        }
        
    except Exception as e:
        print(f"Error in update_scene_image: {str(e)}")
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

@router.delete("/scene-images/{image_id}")
async def delete_scene_image(image_id: str, db: Session = Depends(get_db)):
    """
    Xóa một hình ảnh của scene
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

        # Xóa hình ảnh
        db.delete(scene_image)
        
        # Cập nhật trạng thái scene nếu không còn hình ảnh nào
        if not scene.images:
            scene.image_status = MediaStatus.PENDING.value
        
        db.commit()

        return {"message": "Scene image deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-images-for-script/{script_id}")
async def save_images_for_script(
    script_id: str,
    images: List[dict],
    db: Session = Depends(get_db)
):
    """
    Lưu hình ảnh cho script với các bước kiểm tra:
    1. Kiểm tra script tồn tại
    2. Kiểm tra scene tồn tại
    3. Kiểm tra hình ảnh đã tồn tại chưa
    4. Nếu chưa tồn tại -> lưu mới
    5. Nếu đã tồn tại -> kiểm tra trùng lặp
    6. Nếu không trùng -> thay thế
    7. Nếu trùng -> bỏ qua
    """
    try:
        # Kiểm tra script tồn tại
        script = get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        print(f"Found script: {script.id}")
        
        saved_images = []
        for image_data in images:
            scene_id = image_data.get("scene_id")
            scene_number = image_data.get("scene_number")
            image_url = image_data.get("image_url")
            prompt = image_data.get("prompt")
            
            if not all([scene_id, scene_number, image_url, prompt]):
                print(f"Skipping invalid image data: {image_data}")
                continue
                
            # Kiểm tra scene tồn tại
            scene = db.query(Scene).filter(Scene.id == scene_id).first()
            if not scene:
                print(f"Scene {scene_id} not found, skipping")
                continue
                
            # Kiểm tra hình ảnh đã tồn tại chưa
            existing_images = db.query(SceneImage).filter(SceneImage.scene_id == scene_id).all()
            
            if not existing_images:
                # Chưa có hình ảnh -> lưu mới
                print(f"Creating new image for scene {scene_number}")
                new_image = SceneImage(
                    scene_id=scene_id,
                    image_url=image_url,
                    prompt=prompt,
                    width=1024,
                    height=768,
                    status=MediaStatus.COMPLETED.value
                )
                db.add(new_image)
                saved_images.append({
                    "id": new_image.id,
                    "scene_id": scene_id,
                    "scene_number": scene_number,
                    "image_url": image_url,
                    "prompt": prompt,
                    "status": MediaStatus.COMPLETED.value,
                    "action": "created"
                })
            else:
                # Đã có hình ảnh -> kiểm tra trùng lặp
                is_duplicate = any(img.image_url == image_url for img in existing_images)
                if not is_duplicate:
                    # Không trùng -> thay thế
                    print(f"Replacing existing images for scene {scene_number}")
                    # Xóa hình ảnh cũ
                    for old_image in existing_images:
                        db.delete(old_image)
                    
                    # Tạo hình ảnh mới
                    new_image = SceneImage(
                        scene_id=scene_id,
                        image_url=image_url,
                        prompt=prompt,
                        width=1024,
                        height=768,
                        status=MediaStatus.COMPLETED.value
                    )
                    db.add(new_image)
                    saved_images.append({
                        "id": new_image.id,
                        "scene_id": scene_id,
                        "scene_number": scene_number,
                        "image_url": image_url,
                        "prompt": prompt,
                        "status": MediaStatus.COMPLETED.value,
                        "action": "replaced"
                    })
                else:
                    # Trùng -> bỏ qua
                    print(f"Skipping duplicate image for scene {scene_number}")
                    saved_images.append({
                        "id": existing_images[0].id,
                        "scene_id": scene_id,
                        "scene_number": scene_number,
                        "image_url": image_url,
                        "prompt": prompt,
                        "status": MediaStatus.COMPLETED.value,
                        "action": "skipped"
                    })
        
        # Cập nhật trạng thái của scenes và script
        for scene in script.scenes:
            scene.image_status = MediaStatus.COMPLETED.value
        
        script.status = ScriptStatus.COMPLETED.value
        db.commit()
        
        return {
            "message": f"Successfully processed {len(saved_images)} images",
            "images": saved_images
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error saving images: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_image_api():
    """
    Endpoint test để kiểm tra API hoạt động
    """
    return {"message": "Image API is working", "status": "ok"} 