from fastapi import APIRouter, HTTPException
from app.schemas.content_suggestion import SearchRequest, SearchResponse
from app.services.youtube_service import YouTubeService
from app.services.tiktok_service import TikTokService
from app.services.google_search_service import GoogleSearchService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Khởi tạo các service
youtube_service = YouTubeService()
tiktok_service = TikTokService()
google_service = GoogleSearchService()

@router.post("/youtube/search", response_model=SearchResponse)
async def search_youtube_videos(request: SearchRequest):
    """
    Tìm kiếm video trên YouTube theo từ khóa
    """
    try:
        videos = youtube_service.search_videos(
            keyword=request.keyword,
            max_results=request.max_results
        )
        return SearchResponse(
            videos=videos,
            total_results=len(videos)
        )
    except Exception as e:
        logger.error(f"Error searching YouTube videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tiktok/search", response_model=SearchResponse)
async def search_tiktok_videos(request: SearchRequest):
    """
    Tìm kiếm video trên TikTok theo từ khóa
    """
    try:
        videos = tiktok_service.search_videos(
            keyword=request.keyword,
            max_results=request.max_results
        )
        return SearchResponse(
            videos=videos,
            total_results=len(videos)
        )
    except Exception as e:
        logger.error(f"Error searching TikTok videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/google/search", response_model=SearchResponse)
async def search_google_videos(request: SearchRequest):
    """
    Tìm kiếm video trên Google theo từ khóa
    """
    try:
        videos = google_service.search_videos(
            keyword=request.keyword,
            max_results=request.max_results
        )
        return SearchResponse(
            videos=videos,
            total_results=len(videos)
        )
    except Exception as e:
        logger.error(f"Error searching Google videos: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 