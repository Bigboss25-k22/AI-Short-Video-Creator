from pydantic import BaseModel, field_validator
from typing import List, Optional, Union
from datetime import datetime

class VisualElementBase(BaseModel):
    element_name: str

class VisualElementCreate(VisualElementBase):
    pass

class VisualElement(VisualElementBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class Scene(BaseModel):
    scene_number: int
    description: str
    duration: int  # Thời lượng tính bằng giây
    visual_elements: str  # Mô tả chi tiết cho việc tạo hình ảnh
    background_music: Optional[str] = None
    voice_over: Optional[str] = None

    class Config:
        from_attributes = True

class VideoScript(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    target_audience: str
    total_duration: int  # Tổng thời lượng tính bằng giây
    scenes: List[Scene]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: str = "draft"  # draft, approved, completed

    class Config:
        from_attributes = True

class CreateScriptRequest(BaseModel):
    topic: str
    target_audience: str
    duration: int 