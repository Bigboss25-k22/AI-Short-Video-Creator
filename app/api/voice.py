from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.google_tts_service import GoogleTTSService
from app.schemas.video_script import VideoScript
from app.schemas.voice import VoiceRequest, VoiceResponse, ScriptVoiceRequest, TextToSpeechRequest, TextToSpeechResponse, UpdateVoiceRequest
from app.crud import video_script as crud
from app.database import get_db
from app.models.video_script import MediaStatus, ScriptStatus
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

class TextToSpeechRequest(BaseModel):
    text: str
    voice_id: str = "en-US-Wavenet-A"  # English female voice
    speed: float = 1.0

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

        return VoiceResponse(
            audio_base64=audio_base64,
            text=request.text,
            voice_id=request.voice_id,
            speed=request.speed
        )

    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
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
        logger.info(f"Generating voices for script: {script_id}")

        # Lấy script từ database
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        # Cập nhật trạng thái script thành processing
        script.status = ScriptStatus.PROCESSING.value
        db.commit()

        responses = []
        # Tạo voice cho từng scene
        for scene in script.scenes:
            if not scene.voice_over:
                continue

            logger.info(f"Generating voice for scene: {scene.id}")

            # Cập nhật trạng thái scene thành processing
            scene.voice_status = MediaStatus.PROCESSING.value
            db.commit()

            try:
                # Tạo voice cho scene
                audio_base64 = google_tts_service.generate_voice(
                    text=scene.voice_over,
                    voice_id=request.voice_id,
                    speed=request.speed
                )

                # Lưu thông tin voice vào database
                audio_data = {
                    "audio_base64": audio_base64,
                    "text_content": scene.voice_over,
                    "voice_id": request.voice_id,
                    "speed": request.speed,
                    "status": MediaStatus.COMPLETED.value
                }
                voice_audio = crud.create_voice_audio(
                    db=db,
                    scene_id=scene.id,
                    audio_data=audio_data
                )

                # Cập nhật trạng thái scene thành completed
                scene.voice_status = MediaStatus.COMPLETED.value
                db.commit()

                responses.append(TextToSpeechResponse(
                    audio_base64=audio_base64,
                    text=scene.voice_over,
                    voice_id=request.voice_id,
                    speed=request.speed,
                    scene_number=scene.scene_number
                ))
            except Exception as e:
                scene.voice_status = MediaStatus.FAILED.value
                db.commit()
                continue

        # Kiểm tra xem tất cả scenes đã hoàn thành chưa
        all_completed = all(scene.voice_status == MediaStatus.COMPLETED.value for scene in script.scenes)
        if all_completed:
            script.status = ScriptStatus.COMPLETED.value
        else:
            script.status = ScriptStatus.FAILED.value
        db.commit()

        return responses
    except Exception as e:
        db.rollback()
        logger.error(f"Error in script_to_speech: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list/{script_id}", response_model=List[TextToSpeechResponse])
async def get_script_voices(script_id: str, db: Session = Depends(get_db)):
    """
    Lấy tất cả các voice audio của một script
    """
    try:
        # Lấy script từ database
        script = crud.get_script(db, script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        responses = []
        # Lấy tất cả voice audio của các scene trong script
        for scene in script.scenes:
            for voice_audio in scene.voice_audios:
                responses.append(TextToSpeechResponse(
                    audio_base64=voice_audio.audio_base64,
                    text=voice_audio.text_content,
                    voice_id=voice_audio.voice_id,
                    speed=voice_audio.speed,
                    scene_number=scene.scene_number
                ))

        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{scene_id}", response_model=TextToSpeechResponse)
async def update_voice(
    scene_id: str,
    request: UpdateVoiceRequest,
    db: Session = Depends(get_db)
):
    """
    Cập nhật voice cho một scene cụ thể
    """
    try:
        # Lấy scene từ database
        scene = crud.get_scene(db, scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        # Cập nhật trạng thái scene thành processing
        scene.voice_status = MediaStatus.PROCESSING.value
        db.commit()

        try:
            # Tạo voice mới cho scene
            audio_base64 = google_tts_service.generate_voice(
                text=request.voice_over,
                voice_id=request.voice_id,
                speed=request.speed
            )

            # Cập nhật voice_over trong scene
            scene.voice_over = request.voice_over
            db.commit()

            # Xóa các voice audio cũ của scene
            for voice_audio in scene.voice_audios:
                db.delete(voice_audio)
            db.commit()

            # Lưu thông tin voice mới vào database
            audio_data = {
                "audio_base64": audio_base64,
                "text_content": request.voice_over,
                "voice_id": request.voice_id,
                "speed": request.speed,
                "status": MediaStatus.COMPLETED.value
            }
            voice_audio = crud.create_voice_audio(
                db=db,
                scene_id=scene.id,
                audio_data=audio_data
            )

            # Cập nhật trạng thái scene thành completed
            scene.voice_status = MediaStatus.COMPLETED.value
            db.commit()

            return TextToSpeechResponse(
                audio_base64=audio_base64,
                text=request.voice_over,
                voice_id=request.voice_id,
                speed=request.speed,
                scene_number=scene.scene_number
            )

        except Exception as e:
            scene.voice_status = MediaStatus.FAILED.value
            db.commit()
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 