from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.google_tts_service import GoogleTTSService
from app.schemas.video_script import VideoScript
from app.schemas.voice import VoiceRequest, VoiceResponse, ScriptVoiceRequest, TextToSpeechRequest, TextToSpeechResponse
from app.crud import video_script as crud
from app.database import get_db
from typing import List
import os
import tempfile
import shutil
from fastapi.responses import Response

router = APIRouter()
google_tts_service = GoogleTTSService()

@router.post("/text-to-speech", response_model=VoiceResponse)
async def text_to_speech(request: VoiceRequest, db: Session = Depends(get_db)):
    """
    Chuyển đổi một đoạn text thành giọng nói và trả về URL để nghe thử
    """
    try:
        # Tạo audio từ text và lấy đường dẫn file
        audio_path = google_tts_service.generate_voice(
            text=request.text,
            voice_id=request.voice_id,
            speed=request.speed
        )
        
        # Lưu thông tin audio vào database
        audio_data = {
            "audio_url": audio_path,
            "text_content": request.text,
            "voice_id": request.voice_id,
            "speed": request.speed
        }
        
        # Trả về đường dẫn audio
        return VoiceResponse(
            url=audio_path,
            text=request.text,
            voice_id=request.voice_id,
            speed=request.speed
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/script-to-speech/{script_id}", response_model=List[TextToSpeechResponse])
async def script_to_speech(
    script_id: str,
    request: TextToSpeechRequest,
    db: Session = Depends(get_db)
):
    """
    Tạo voice cho tất cả các scene trong một video script
    """
    try:
        # Lấy script từ database
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        responses = []
        # Tạo voice cho từng scene
        for scene in script.scenes:
            if not scene.voice_over:
                continue

            # Tạo voice cho scene
            audio_path = google_tts_service.generate_voice(
                text=scene.voice_over,
                voice_id=request.voice_id,
                speed=request.speed
            )

            # Lưu thông tin voice vào database
            voice_audio = crud.create_voice_audio(db, {
                "script_id": script_id,
                "scene_id": scene.id,
                "audio_url": audio_path,
                "text_content": scene.voice_over,
                "voice_id": request.voice_id,
                "speed": request.speed
            })

            responses.append(TextToSpeechResponse(
                audio_url=audio_path,
                text=scene.voice_over,
                voice_id=request.voice_id,
                speed=request.speed
            ))

        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 