from fastapi import APIRouter, HTTPException, Body, UploadFile, File
from google.cloud import storage
import datetime
import uuid
import logging
from pydantic import BaseModel

# Thiết lập logging
logger = logging.getLogger(__name__)

class FileInfo(BaseModel):
    file_name: str
    content_type: str

router = APIRouter()

# THAY THẾ BẰNG TÊN BUCKET CỦA BẠN TRÊN GOOGLE CLOUD STORAGE
# Ví dụ: nếu project ID là "my-project-123" thì bucket thường là "my-project-123.appspot.com"
BUCKET_NAME = "al-short-video-creator-storage"  # Thay đổi thành bucket thực tế của bạn

@router.post("/generate-upload-url", summary="Generate a signed URL for uploading a file")
async def generate_upload_url(file_info: FileInfo):
    """
    Tạo một URL có chữ ký để client có thể upload file trực tiếp lên GCS.
    """
    try:
        logger.info(f"Generating upload URL for file: {file_info.file_name}")
        
        # Kiểm tra xem có credentials không
        try:
            storage_client = storage.Client()
            logger.info("Google Cloud Storage client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
            raise HTTPException(
                status_code=500, 
                detail="Google Cloud Storage credentials not configured. Please set GOOGLE_APPLICATION_CREDENTIALS environment variable."
            )
        
        # Kiểm tra bucket có tồn tại không
        try:
            bucket = storage_client.bucket(BUCKET_NAME)
            # Kiểm tra bucket có tồn tại không
            if not bucket.exists():
                logger.error(f"Bucket {BUCKET_NAME} does not exist")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Bucket {BUCKET_NAME} does not exist. Please create it in Google Cloud Console."
                )
        except Exception as e:
            logger.error(f"Error accessing bucket {BUCKET_NAME}: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error accessing bucket {BUCKET_NAME}. Please check your configuration."
            )
        
        unique_blob_name = f"videos/{uuid.uuid4()}-{file_info.file_name}"
        blob = bucket.blob(unique_blob_name)

        # Tạo URL để upload (dùng phương thức PUT)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="PUT",
            content_type=file_info.content_type,
        )
        
        # URL công khai để truy cập file sau khi upload xong
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{unique_blob_name}"

        logger.info(f"Generated upload URL successfully for {unique_blob_name}")
        return {"upload_url": url, "public_url": public_url}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating signed URL: {e}")
        raise HTTPException(status_code=500, detail=f"Could not generate upload URL: {str(e)}")

@router.post("/upload-video", summary="Upload video file to Google Cloud Storage")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload video file trực tiếp lên Google Cloud Storage qua backend.
    """
    try:
        logger.info(f"Uploading video file: {file.filename}")
        
        # Kiểm tra file type
        if not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Kiểm tra file size (giới hạn 100MB)
        content = await file.read()
        if len(content) > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(status_code=400, detail="File size too large (max 100MB)")
        
        # Khởi tạo Google Cloud Storage client
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
            raise HTTPException(
                status_code=500, 
                detail="Google Cloud Storage credentials not configured."
            )
        
        # Tạo tên file duy nhất
        unique_blob_name = f"videos/{uuid.uuid4()}-{file.filename}"
        blob = bucket.blob(unique_blob_name)
        
        # Upload file lên Google Cloud Storage
        blob.upload_from_string(
            content,
            content_type=file.content_type
        )
        
        # Tạo signed URL để xem video (có hiệu lực 1 giờ)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET",
        )
        
        # URL công khai (nếu bucket public)
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{unique_blob_name}"
        
        logger.info(f"Video uploaded successfully: {unique_blob_name}")
        return {
            "public_url": public_url, 
            "signed_url": signed_url,
            "filename": unique_blob_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")

@router.get("/get-video-url/{filename:path}", summary="Get signed URL for viewing video")
async def get_video_url(filename: str):
    """
    Tạo signed URL để xem video (nếu bucket không public).
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        
        # Kiểm tra file có tồn tại không
        if not blob.exists():
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Tạo signed URL có hiệu lực 1 giờ
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET",
        )
        
        return {"signed_url": signed_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating video URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate video URL: {str(e)}")

async def upload_image_to_cloud(image_file, filename: str):
    """
    Upload image file lên Google Cloud Storage và trả về public URL
    """
    try:
        logger.info(f"Uploading image file: {filename}")
        
        # Khởi tạo Google Cloud Storage client
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
            raise Exception("Google Cloud Storage credentials not configured.")
        
        # Tạo blob và upload
        blob = bucket.blob(filename)
        blob.upload_from_file(image_file, content_type='image/jpeg')
        
        # URL công khai
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        
        logger.info(f"Image uploaded successfully: {filename}")
        return public_url
        
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise Exception(f"Failed to upload image: {str(e)}")
