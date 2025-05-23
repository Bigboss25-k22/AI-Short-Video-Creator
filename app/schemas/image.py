from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ImageGenerationRequest(BaseModel):
    scene_id: str
    prompt: Optional[str] = None
    width: Optional[int] = 1024
    height: Optional[int] = 768

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
    created_at: datetime

    class Config:
        from_attributes = True 