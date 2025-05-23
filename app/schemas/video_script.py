from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Scene(BaseModel):
    scene_number: int
    description: str
    duration: int  # Thời lượng tính bằng giây
    visual_elements: List[str]
    background_music: Optional[str] = None
    voice_over: Optional[str] = None

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

class CreateScriptRequest(BaseModel):
    topic: str
    target_audience: str
    duration: int 