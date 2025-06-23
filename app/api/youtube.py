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
    channel_id: str = Query(..., description="YouTube channel ID"),
    max_results: int = Query(20, ge=1, le=50, description="Số video tối đa trả về"),
    page_token: str = Query(None, description="Page token cho phân trang")
):
    """
    Lấy danh sách video của kênh kèm thống kê chi tiết từng video
    """
    result = youtube_service.get_channel_videos_with_stats(channel_id, max_results, page_token)
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
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập hoặc thiếu access token")
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
        response = youtube_service.upload_video(
            access_token=access_token,
            title=title,
            description=description,
            file_path=temp_file_path,
            privacy_status=privacy_status
        )
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
    Lấy danh sách video của kênh người dùng hiện tại (tự động lấy channel_id từ access_token trong cookie)
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập hoặc thiếu access token")
    # Lấy channel_id từ access_token
    try:
        credentials = Credentials(token=access_token)
        youtube = build('youtube', 'v3', credentials=credentials)
        response = youtube.channels().list(part='id', mine=True).execute()
        if not response['items']:
            raise HTTPException(status_code=404, detail="Không tìm thấy kênh YouTube cho người dùng này")
        channel_id = response['items'][0]['id']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không lấy được channel_id: {e}")
    # Lấy danh sách video như cũ
    result = youtube_service.get_channel_videos_with_stats(channel_id, max_results, page_token)
    if not result['videos']:
        raise HTTPException(status_code=404, detail="Không tìm thấy video nào cho kênh này hoặc có lỗi xảy ra.")
    return result 

@router.get("/my/stats")
def get_my_channel_stats(request: Request):
    """
    Lấy thống kê cơ bản về kênh YouTube của người dùng hiện tại (subscribers, tổng view, tổng video, tên kênh, mô tả, avatar, ngày tạo...)
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập hoặc thiếu access token")
    try:
        credentials = Credentials(token=access_token)
        youtube = build('youtube', 'v3', credentials=credentials)
        response = youtube.channels().list(part='snippet,statistics', mine=True).execute()
        if not response['items']:
            raise HTTPException(status_code=404, detail="Không tìm thấy kênh YouTube cho người dùng này")
        item = response['items'][0]
        stats = {
            'channel_id': item['id'],
            'title': item['snippet']['title'],
            'description': item['snippet'].get('description', ''),
            'published_at': item['snippet']['publishedAt'],
            'avatar_url': item['snippet']['thumbnails']['high']['url'],
            'subscriber_count': int(item['statistics'].get('subscriberCount', 0)),
            'view_count': int(item['statistics'].get('viewCount', 0)),
            'video_count': int(item['statistics'].get('videoCount', 0)),
        }
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không lấy được thống kê kênh: {e}") 