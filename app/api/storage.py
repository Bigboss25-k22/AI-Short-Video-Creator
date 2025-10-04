from fastapi import APIRouter, HTTPException, UploadFile, File
from google.cloud import storage
import datetime
import uuid
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FileInfo(BaseModel):
    file_name: str
    content_type: str


router = APIRouter()

BUCKET_NAME = "al-short-video-creator-storage"


@router.post(
    "/generate-upload-url", summary="Generate a signed URL for uploading a file"
)
async def generate_upload_url(file_info: FileInfo):
    """Tạo một URL có chữ ký để client có thể upload file trực tiếp lên GCS."""
    try:
        storage_client = storage.Client()
    except Exception as e:
        logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
        raise HTTPException(
            status_code=500,
            detail="Google Cloud Storage credentials not configured. Please set GOOGLE_APPLICATION_CREDENTIALS environment variable.",
        )

    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        if not bucket.exists():
            logger.error(f"Bucket {BUCKET_NAME} does not exist")
            raise HTTPException(
                status_code=500,
                detail=f"Bucket {BUCKET_NAME} does not exist. Please create it in Google Cloud Console.",
            )
    except Exception as e:
        logger.error(f"Error accessing bucket {BUCKET_NAME}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error accessing bucket {BUCKET_NAME}. Please check your configuration.",
        )

    unique_blob_name = f"videos/{uuid.uuid4()}-{file_info.file_name}"
    blob = bucket.blob(unique_blob_name)

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=15),
        method="PUT",
        content_type=file_info.content_type,
    )

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{unique_blob_name}"
    return {"upload_url": url, "public_url": public_url}


@router.post("/upload-video", summary="Upload video file to Google Cloud Storage")
async def upload_video(file: UploadFile = File(...)):
    """Upload video file trực tiếp lên Google Cloud Storage qua backend."""
    try:
        if not file.content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail="File must be a video")

        content = await file.read()
        if len(content) > 100 * 1024 * 1024:
            raise HTTPException(
                status_code=400, detail="File size too large (max 100MB)"
            )

        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
            raise HTTPException(
                status_code=500,
                detail="Google Cloud Storage credentials not configured.",
            )

        unique_blob_name = f"videos/{uuid.uuid4()}-{file.filename}"
        blob = bucket.blob(unique_blob_name)

        blob.upload_from_string(content, content_type=file.content_type)

        signed_url = blob.generate_signed_url(
            version="v4", expiration=datetime.timedelta(hours=1), method="GET"
        )

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{unique_blob_name}"
        return {
            "public_url": public_url,
            "signed_url": signed_url,
            "filename": unique_blob_name,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")


@router.get(
    "/get-video-url/{filename:path}", summary="Get signed URL for viewing video"
)
async def get_video_url(filename: str):
    """Tạo signed URL để xem video (nếu bucket không public)."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)

        if not blob.exists():
            raise HTTPException(status_code=404, detail="Video not found")

        signed_url = blob.generate_signed_url(
            version="v4", expiration=datetime.timedelta(hours=1), method="GET"
        )

        return {"signed_url": signed_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating video URL: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate video URL: {str(e)}"
        )


@router.get(
    "/get-image-url/{filename:path}", summary="Get signed URL for viewing image"
)
async def get_image_url(filename: str):
    """Tạo signed URL để xem ảnh (nếu bucket không public)."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)

        if not blob.exists():
            raise HTTPException(status_code=404, detail="Image not found")

        signed_url = blob.generate_signed_url(
            version="v4", expiration=datetime.timedelta(hours=1), method="GET"
        )

        return {"signed_url": signed_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating image URL: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate image URL: {str(e)}"
        )


async def get_signed_image_url(image_url: str):
    """Chuyển đổi Google Cloud Storage URL thành signed URL"""
    try:
        if not image_url.startswith("https://storage.googleapis.com/"):
            return image_url

        filename = image_url.replace(
            f"https://storage.googleapis.com/{BUCKET_NAME}/", ""
        )

        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)

        if not blob.exists():
            return image_url

        signed_url = blob.generate_signed_url(
            version="v4", expiration=datetime.timedelta(hours=1), method="GET"
        )

        return signed_url

    except Exception as e:
        logger.error(f"Error generating signed image URL: {e}")
        return image_url


async def upload_image_to_cloud(image_file, filename: str):
    """Upload image file lên Google Cloud Storage và trả về public URL"""
    try:
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
            raise Exception("Google Cloud Storage credentials not configured.")

        blob = bucket.blob(filename)
        blob.upload_from_file(image_file, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return public_url

    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise Exception(f"Failed to upload image: {str(e)}")
