from pydantic import BaseModel
from app.schemas.video_script import VideoScript
from typing import List, Optional

class VoiceRequest(BaseModel):
    text: str
    voice_id: str = "vi-VN-Wavenet-A"  # Vietnamese female voice
    speed: float = 1.0

class VoiceResponse(BaseModel):
    url: str
    text: str
    voice_id: str
    speed: float

class ScriptVoiceRequest(BaseModel):
    script_id: str
    voice_id: str = "vi-VN-Wavenet-A"  # Vietnamese female voice
    speed: float = 1.0

class TextToSpeechRequest(BaseModel):
    voice_id: str = "vi-VN-Wavenet-A"  # Vietnamese female voice
    speed: float = 1.0

class TextToSpeechResponse(BaseModel):
    audio_url: str
    text: str
    voice_id: str
    speed: float 