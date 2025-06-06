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
import base64
import logging
from fastapi.responses import Response
from pydub import AudioSegment
import io

logger = logging.getLogger(__name__)
router = APIRouter()
google_tts_service = GoogleTTSService()

@router.post("/text-to-speech", response_model=VoiceResponse)
async def text_to_speech(request: VoiceRequest, db: Session = Depends(get_db)):
    """
    Chuyển đổi một đoạn text thành giọng nói và trả về base64 audio
    """
    try:
        logger.info(f"Generating voice for text: {request.text[:100]}...")
        
        # Tạo audio base64 từ text
        audio_base64 = google_tts_service.generate_voice(
            text=request.text,
            voice_id=request.voice_id,
            speed=request.speed
        )
        
        logger.info("Successfully generated base64 audio")
        
        # Tạo file tạm để lưu audio
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                # Giải mã base64 và lưu vào file
                audio_bytes = base64.b64decode(audio_base64)
                temp_file.write(audio_bytes)
                audio_path = temp_file.name
                logger.info(f"Successfully saved audio to temporary file: {audio_path}")
        except Exception as e:
            logger.error(f"Error saving audio to file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error saving audio: {str(e)}")
        
        # Trả về base64 audio
        return VoiceResponse(
            audio_base64=audio_base64,
            audio_url=audio_path,
            text=request.text,
            voice_id=request.voice_id,
            speed=request.speed
        )
            
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/script-to-speech/{script_id}", response_model=TextToSpeechResponse)
async def script_to_speech(
    script_id: str,
    request: TextToSpeechRequest,
    db: Session = Depends(get_db)
):
    """
    Tạo voice cho tất cả các scene trong một video script và kết hợp thành một file duy nhất
    """
    try:
        logger.info(f"Generating voices for script: {script_id}")
        
        # Lấy script từ database
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        # Tạo voice cho từng scene
        scene_audios = []
        audio_segments = []

        for scene in script.scenes:
            if not scene.voice_over:
                continue

            logger.info(f"Generating voice for scene: {scene.id}")
            
            # Tạo voice cho scene
            audio_base64 = google_tts_service.generate_voice(
                text=scene.voice_over,
                voice_id=request.voice_id,
                speed=request.speed
            )

            # Chuyển base64 thành AudioSegment
            audio_bytes = base64.b64decode(audio_base64)
            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            audio_segments.append(audio_segment)

            # Lưu thông tin voice vào database
            audio_data = {
                "audio_base64": audio_base64,
                "text_content": scene.voice_over,
                "voice_id": request.voice_id,
                "speed": request.speed
            }
            voice_audio = crud.create_voice_audio(
                db=db,
                script_id=script_id,
                scene_id=scene.id,
                audio_data=audio_data
            )

            scene_audios.append({
                "audio_base64": audio_base64,
                "text": scene.voice_over,
                "voice_id": request.voice_id,
                "speed": request.speed
            })

        # Kết hợp các audio segment
        try:
            combined_audio = AudioSegment.empty()
            for segment in audio_segments:
                combined_audio += segment

            # Chuyển đổi audio kết hợp thành base64
            buffer = io.BytesIO()
            combined_audio.export(buffer, format="mp3")
            combined_audio_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            return TextToSpeechResponse(
                audio_base64=combined_audio_base64,
                text="Combined audio from all scenes",
                voice_id=request.voice_id,
                speed=request.speed
            )

        except Exception as e:
            logger.error(f"Error combining audio: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error combining audio: {str(e)}")

    except Exception as e:
        logger.error(f"Error in script_to_speech: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 