import os
import logging
from google.cloud import texttospeech
from google.auth.exceptions import DefaultCredentialsError
from typing import List
import tempfile
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class GoogleTTSService:
    def __init__(self):
        try:
            settings = get_settings()
            # Log thông tin về credentials
            creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS
            logger.info(f"Looking for credentials at: {creds_path}")
            
            if not creds_path:
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set in .env file")
            
            if not os.path.exists(creds_path):
                raise ValueError(f"Credentials file not found at: {creds_path}")
            
            # Kiểm tra quyền truy cập file
            if not os.access(creds_path, os.R_OK):
                raise ValueError(f"Cannot read credentials file at: {creds_path}")
            
            logger.info("Credentials file found and readable")
            
            # Thiết lập biến môi trường
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
            
            # Khởi tạo client
            self.client = texttospeech.TextToSpeechClient()
            logger.info("GoogleTTSService initialized successfully")
            
        except DefaultCredentialsError as e:
            logger.error(f"Google Cloud credentials error: {str(e)}")
            raise ValueError(
                "Google Cloud credentials error. Please check:\n"
                "1. The credentials file exists and is readable\n"
                "2. The credentials file contains valid JSON\n"
                "3. The service account has the necessary permissions\n"
                f"Current credentials path: {settings.GOOGLE_APPLICATION_CREDENTIALS}"
            )
        except Exception as e:
            logger.error(f"Unexpected error initializing GoogleTTSService: {str(e)}")
            raise

    def generate_voice(self, text: str, voice_id: str = "vi-VN-Wavenet-A", speed: float = 1.0) -> str:
        """
        Tạo file audio từ text sử dụng Google TTS
        
        Args:
            text: Văn bản cần chuyển thành giọng nói
            voice_id: ID của giọng đọc (mặc định: vi-VN-Wavenet-A)
            speed: Tốc độ đọc (0.25 - 4.0)
            
        Returns:
            str: Đường dẫn đến file audio
        """
        try:
            logger.info(f"Generating voice for text length: {len(text)}")
            logger.info(f"Using voice: {voice_id}, speed: {speed}")

            # Cấu hình input
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Cấu hình voice
            voice = texttospeech.VoiceSelectionParams(
                language_code="vi-VN",
                name=voice_id
            )

            # Cấu hình audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speed
            )

            # Gọi API để tạo audio
            logger.info("Calling Google TTS API...")
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            logger.info("Successfully received response from Google TTS API")

            # Tạo file tạm để lưu audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(response.audio_content)
                temp_file_path = temp_file.name

            logger.info(f"Successfully generated audio file: {temp_file_path}")
            return temp_file_path

        except Exception as e:
            logger.error(f"Error generating voice: {str(e)}")
            raise

    def generate_voices_for_script(self, script_texts: List[str], output_dir: str) -> List[str]:
        """
        Tạo các file audio cho toàn bộ script
        
        Args:
            script_texts: Danh sách các đoạn text cần chuyển thành giọng nói
            output_dir: Thư mục lưu các file audio
            
        Returns:
            List[str]: Danh sách đường dẫn đến các file audio đã tạo
        """
        try:
            logger.info(f"Generating voices for script with {len(script_texts)} scenes")
            logger.info(f"Output directory: {output_dir}")

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"Created output directory: {output_dir}")

            audio_files = []
            for i, text in enumerate(script_texts):
                logger.info(f"Processing scene {i+1}/{len(script_texts)}")
                
                # Tạo audio file
                audio_path = self.generate_voice(text)
                
                # Di chuyển file vào thư mục output
                filename = f"scene_{i+1}.mp3"
                output_path = os.path.join(output_dir, filename)
                os.rename(audio_path, output_path)
                
                audio_files.append(output_path)
                logger.info(f"Created audio file: {output_path}")

            return audio_files

        except Exception as e:
            logger.error(f"Error generating voices for script: {str(e)}")
            raise