from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.google_tts_service import GoogleTTSService
from app.schemas.video_script import VideoScript
from app.schemas.voice import VoiceRequest, VoiceResponse, ScriptVoiceRequest
from app.crud import video_script as crud
from app.database import get_db
from typing import List
import os
import tempfile
import shutil
from pydantic import BaseModel
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

@router.post("/script-to-speech")
async def script_to_speech(request: ScriptVoiceRequest, db: Session = Depends(get_db)):
    """
    Tạo file audio cho toàn bộ script
    """
    try:
        # Kiểm tra script tồn tại
        script = crud.get_script(db, request.script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        
        # Tạo thư mục tạm để lưu file audio
        with tempfile.TemporaryDirectory() as temp_dir:
            # Lấy danh sách text từ script
            script_texts = [scene.voice_over for scene in script.scenes if scene.voice_over]
            
            # Tạo các file audio
            audio_paths = google_tts_service.generate_voices_for_script(script_texts, temp_dir)
            
            # Lưu thông tin audio vào database
            for scene, audio_path in zip(script.scenes, audio_paths):
                if scene.voice_over:
                    crud.create_voice_audio(db, request.script_id, scene.id, {
                        "audio_url": audio_path,
                        "text_content": scene.voice_over,
                        "voice_id": request.voice_id,
                        "speed": request.speed
                    })
            
            # Tạo file zip chứa tất cả audio
            zip_path = os.path.join(temp_dir, "audio_files.zip")
            shutil.make_archive(zip_path[:-4], 'zip', temp_dir)
            
            # Đọc file zip
            with open(zip_path, "rb") as f:
                zip_data = f.read()
            
            # Trả về file zip
            return Response(
                content=zip_data,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=script_audio_{script.title}.zip"
                }
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 