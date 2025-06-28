from fastapi import APIRouter, HTTPException, Query, File, UploadFile, Form, Request
from app.services.youtube_service import YouTubeService
import shutil
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import requests

router = APIRouter(prefix="/youtube", tags=["youtube"])

youtube_service = YouTubeService()

@router.get("/channel/videos")
def get_channel_videos(
    request: Request,
    channel_id: str = Query(..., description="YouTube channel ID"),
    max_results: int = Query(20, ge=1, le=50, description="Số video tối đa trả về"),
    page_token: str = Query(None, description="Page token cho phân trang")
):
    """
    Lấy danh sách video của kênh kèm thống kê chi tiết từng video
    """
    google_access_token = request.cookies.get("google_access_token")
    result = youtube_service.get_channel_videos_with_stats(channel_id, max_results, page_token, google_access_token)
    if not result['videos']:
        raise HTTPException(status_code=404, detail="Không tìm thấy video nào cho kênh này hoặc có lỗi xảy ra.")
    return result

@router.post("/upload")
def upload_video(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    privacy_status: str = Form("private"),
    file: UploadFile = File(None),
    file_url: str = Form(None)
):
    """
    Đăng tải video lên YouTube (tự lấy access_token từ cookie, hỗ trợ upload file hoặc từ URL)
    """
    google_access_token = request.cookies.get("google_access_token")
    google_refresh_token = request.cookies.get("google_refresh_token")
    
    if not google_access_token:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập Google hoặc thiếu Google access token")
    
    temp_file_path = None
    try:
        if file is not None:
            temp_file_path = f"temp_{file.filename}"
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        elif file_url:
            # Tải file từ URL về tạm
            temp_file_path = "temp_video_from_url"
            with requests.get(file_url, stream=True) as r:
                r.raise_for_status()
                with open(temp_file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        else:
            raise HTTPException(status_code=400, detail="Phải upload file hoặc cung cấp file_url")
        
        # Thử upload với access token hiện tại
        response = youtube_service.upload_video(
            access_token=google_access_token,
            title=title,
            description=description,
            file_path=temp_file_path,
            privacy_status=privacy_status,
            refresh_token=google_refresh_token
        )
        
        # Kiểm tra nếu có lỗi
        if isinstance(response, dict) and response.get('error'):
            raise HTTPException(status_code=400, detail=response['error'])
        
        if not response:
            # Nếu thất bại, thử refresh token
            if google_refresh_token:
                new_access_token = youtube_service.refresh_google_token(google_refresh_token)
                if new_access_token:
                    response = youtube_service.upload_video(
                        access_token=new_access_token,
                        title=title,
                        description=description,
                        file_path=temp_file_path,
                        privacy_status=privacy_status,
                        refresh_token=google_refresh_token
                    )
                    
                    # Kiểm tra lỗi sau khi refresh
                    if isinstance(response, dict) and response.get('error'):
                        raise HTTPException(status_code=400, detail=response['error'])
            
            if not response:
                raise HTTPException(status_code=500, detail="Đăng tải video thất bại.")
        
        return response
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.delete("/video/{video_id}")
def delete_video(
    video_id: str,
    access_token: str = Query(..., description="OAuth2 access token")
):
    """
    Xóa video khỏi YouTube
    """
    success = youtube_service.delete_video(access_token, video_id)
    if not success:
        raise HTTPException(status_code=500, detail="Xóa video thất bại.")
    return {"msg": "Xóa video thành công."}

@router.get("/my/videos")
def get_my_videos(
    request: Request,
    max_results: int = Query(20, ge=1, le=50, description="Số video tối đa trả về"),
    page_token: str = Query(None, description="Page token cho phân trang")
):
    """
    Lấy danh sách video của kênh người dùng hiện tại
    """
    google_access_token = request.cookies.get("google_access_token")
    if not google_access_token:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập Google hoặc thiếu Google access token")
    
    try:
        result = youtube_service.get_my_videos(google_access_token, max_results, page_token)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không lấy được danh sách video: {e}")

@router.get("/my/channel-id")
def get_my_channel_id(request: Request):
    """
    Lấy channel ID của kênh YouTube của người dùng hiện tại
    """
    google_access_token = request.cookies.get("google_access_token")
    if not google_access_token:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập Google hoặc thiếu Google access token")
    
    try:
        channel_id = youtube_service.get_my_channel_id(google_access_token)
        return {"channel_id": channel_id} if channel_id else None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không lấy được channel ID: {e}")

@router.get("/my/stats")
def get_my_channel_stats(request: Request):
    """
    Lấy thống kê cơ bản về kênh YouTube của người dùng hiện tại
    """
    google_access_token = request.cookies.get("google_access_token")
    if not google_access_token:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập Google hoặc thiếu Google access token")
    
    try:
        stats = youtube_service.get_my_channel_stats(google_access_token)
        return stats if stats else None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không lấy được thống kê kênh: {e}")

@router.post("/refresh-token")
def refresh_google_token(request: Request):
    """
    Refresh Google access token
    """
    google_refresh_token = request.cookies.get("google_refresh_token")
    if not google_refresh_token:
        raise HTTPException(status_code=401, detail="Không có refresh token")
    
    new_access_token = youtube_service.refresh_google_token(google_refresh_token)
    if not new_access_token:
        raise HTTPException(status_code=500, detail="Không thể refresh token")
    
    return {"access_token": new_access_token} 