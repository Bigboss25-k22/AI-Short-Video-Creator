from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ImageGenerationRequest(BaseModel):
    scene_id: str
    prompt: Optional[str] = None
    width: int = 1024
    height: int = 768

class SceneImageBase(BaseModel):
    image_url: str
    prompt: str
    width: int
    height: int

class SceneImageCreate(SceneImageBase):
    scene_id: str

class SceneImage(SceneImageBase):
    id: str
    scene_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ImageGenerationResponse(BaseModel):
    id: str
    scene_id: str
    image_url: str
    prompt: str
    width: int
    height: int
    status: str
    scene_number: int

class UpdateSceneImageRequest(BaseModel):
    prompt: str
    width: Optional[int] = None
    height: Optional[int] = None 