from pydantic import BaseModel
from app.schemas.video_script import VideoScript
from typing import List, Optional

class VoiceRequest(BaseModel):
    text: str
    voice_id: str = "vi-VN-Wavenet-A"  # Default to Vietnamese female voice
    speed: float = 1.0  # Range: 0.25 - 4.0

class VoiceResponse(BaseModel):
    url: str
    text: str
    voice_id: str
    speed: float

class ScriptVoiceRequest(BaseModel):
    script_id: str
    script: VideoScript
    voice_id: Optional[str] = "vi-VN-Wavenet-A"
    speed: Optional[float] = 1.0 