from fastapi import APIRouter, HTTPException
from typing import Dict, List
import requests
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import os
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Khởi tạo YouTube client
def get_youtube_client():
    settings = get_settings()
    return build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)

# Khởi tạo Google Custom Search client
def get_google_search_client():
    settings = get_settings()
    return build('customsearch', 'v1', developerKey=settings.GOOGLE_API_KEY)

@router.get("/youtube/{keyword}")
async def search_youtube(keyword: str, max_results: int = 10):
    """
    Tìm kiếm video trên YouTube
    """
    try:
        youtube = get_youtube_client()
        
        # Tìm kiếm video
        search_response = youtube.search().list(
            q=keyword,
            part='snippet',
            maxResults=max_results,
            type='video',
            videoDuration='short',
            order='viewCount'
        ).execute()

        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        
        # Lấy thông tin chi tiết
        videos_response = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(video_ids)
        ).execute()

        videos = []
        for item in videos_response.get('items', []):
            video = {
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'url': f"https://www.youtube.com/watch?v={item['id']}",
                'thumbnail_url': item['snippet']['thumbnails']['high']['url'],
                'view_count': int(item['statistics']['viewCount']),
                'like_count': int(item['statistics'].get('likeCount', 0)),
                'published_at': item['snippet']['publishedAt'],
                'duration': item['contentDetails']['duration'],
                'channel_name': item['snippet']['channelTitle']
            }
            videos.append(video)

        return {'videos': videos, 'total': len(videos)}

    except Exception as e:
        logger.error(f"Error searching YouTube: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/google/{keyword}")
async def search_google(keyword: str, max_results: int = 10):
    """
    Tìm kiếm video trên Google (sử dụng YouTube API)
    """
    try:
        youtube = get_youtube_client()
        
        # Tìm kiếm video
        search_response = youtube.search().list(
            q=keyword,
            part='snippet',
            maxResults=max_results,
            type='video',
            videoDuration='short',
            order='viewCount'
        ).execute()

        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        
        # Lấy thông tin chi tiết
        videos_response = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(video_ids)
        ).execute()

        videos = []
        for item in videos_response.get('items', []):
            video = {
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'url': f"https://www.youtube.com/watch?v={item['id']}",
                'thumbnail_url': item['snippet']['thumbnails']['high']['url'],
                'view_count': int(item['statistics']['viewCount']),
                'like_count': int(item['statistics'].get('likeCount', 0)),
                'published_at': item['snippet']['publishedAt'],
                'duration': item['contentDetails']['duration'],
                'channel_name': item['snippet']['channelTitle'],
                'platform': 'youtube'
            }
            videos.append(video)

        return {'videos': videos, 'total': len(videos)}

    except Exception as e:
        logger.error(f"Error searching Google: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tiktok/{keyword}")
async def search_tiktok(
    keyword: str, 
    cursor: str = "0",
    search_id: str = "0"
):
    """
    Tìm kiếm video trên TikTok sử dụng RapidAPI
    """
    try:
        settings = get_settings()
        
        # Gọi TikTok API thông qua RapidAPI
        url = "https://tiktok-api23.p.rapidapi.com/api/search/general"
        headers = {
            "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
            "X-RapidAPI-Host": "tiktok-api23.p.rapidapi.com"
        }
        params = {
            "keyword": keyword,
            "cursor": cursor,
            "search_id": search_id
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        # Kiểm tra lỗi chi tiết
        if response.status_code == 403:
            logger.error("TikTok API access forbidden. Please check your API key and subscription status.")
            raise HTTPException(
                status_code=403,
                detail="Access to TikTok API is forbidden. Please check your API key and subscription status."
            )
        elif response.status_code == 429:
            logger.error("TikTok API rate limit exceeded.")
            raise HTTPException(
                status_code=429,
                detail="TikTok API rate limit exceeded. Please try again later."
            )
        
        response.raise_for_status()
        data = response.json()

        # Xử lý dữ liệu từ response
        videos = []
        items = data.get('data', [])
        
        # Kiểm tra nếu items là list
        if isinstance(items, list):
            for item in items:
                if item.get('type') == 'video':
                    video = {
                        'title': item.get('title', ''),
                        'description': item.get('desc', ''),
                        'url': item.get('video_url', ''),
                        'thumbnail_url': item.get('cover', ''),
                        'view_count': item.get('play_count', 0),
                        'like_count': item.get('digg_count', 0),
                        'published_at': datetime.fromtimestamp(item.get('create_time', 0)).isoformat(),
                        'channel_name': item.get('author', {}).get('nickname', ''),
                        'platform': 'tiktok',
                        'music': item.get('music', {}).get('title', ''),
                        'duration': item.get('duration', 0),
                        'share_count': item.get('share_count', 0),
                        'comment_count': item.get('comment_count', 0)
                    }
                    videos.append(video)

        # Lấy cursor và search_id cho trang tiếp theo
        next_cursor = data.get('cursor', '0')
        next_search_id = data.get('search_id', '0')
        
        if next_cursor == '-1':
            next_cursor = None

        return {
            'videos': videos,
            'total': len(videos),
            'has_more': len(videos) > 0,
            'cursor': next_cursor,
            'search_id': next_search_id
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling TikTok API: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error calling TikTok API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error searching TikTok: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching TikTok: {str(e)}"
        )

@router.get("/tiktok/user/{sec_uid}")
async def get_user_posts(
    sec_uid: str,
    max_results: int = 35,
    cursor: str = "0"
):
    """
    Lấy danh sách video của một user TikTok
    """
    try:
        settings = get_settings()
        
        # Gọi TikTok API thông qua RapidAPI
        url = "https://tiktok-api23.p.rapidapi.com/api/user/posts"
        headers = {
            "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
            "X-RapidAPI-Host": "tiktok-api23.p.rapidapi.com"
        }
        params = {
            "secUid": sec_uid,
            "count": max_results,
            "cursor": cursor
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        # Kiểm tra lỗi chi tiết
        if response.status_code == 403:
            logger.error("TikTok API access forbidden. Please check your API key and subscription status.")
            raise HTTPException(
                status_code=403,
                detail="Access to TikTok API is forbidden. Please check your API key and subscription status."
            )
        elif response.status_code == 429:
            logger.error("TikTok API rate limit exceeded.")
            raise HTTPException(
                status_code=429,
                detail="TikTok API rate limit exceeded. Please try again later."
            )
        
        response.raise_for_status()
        data = response.json()

        # Xử lý dữ liệu từ response
        videos = []
        for item in data.get('data', {}).get('itemList', []):
            video = {
                'title': item.get('title', ''),
                'description': item.get('desc', ''),
                'url': item.get('video_url', ''),
                'thumbnail_url': item.get('cover', ''),
                'view_count': item.get('play_count', 0),
                'like_count': item.get('digg_count', 0),
                'published_at': datetime.fromtimestamp(item.get('create_time', 0)).isoformat(),
                'channel_name': item.get('author', {}).get('nickname', ''),
                'platform': 'tiktok',
                'music': item.get('music', {}).get('title', ''),
                'duration': item.get('duration', 0),
                'share_count': item.get('share_count', 0),
                'comment_count': item.get('comment_count', 0)
            }
            videos.append(video)

        # Lấy cursor cho trang tiếp theo
        next_cursor = data.get('data', {}).get('cursor')
        if next_cursor == '-1':
            next_cursor = None

        return {
            'videos': videos,
            'total': len(videos),
            'has_more': data.get('data', {}).get('hasMore', False),
            'cursor': next_cursor,
            'extra': data.get('data', {}).get('extra', {})
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling TikTok API: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error calling TikTok API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting user posts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting user posts: {str(e)}"
        )

@router.get("/tiktok/trending")
async def get_tiktok_trending(
    page: int = 1,
    limit: int = 20,
    period: int = 30,
    order_by: str = "vv",
    country: str = "US"
):
    """
    Lấy danh sách video trending trên TikTok
    """
    try:
        settings = get_settings()
        
        # Gọi TikTok API thông qua RapidAPI
        url = "https://tiktok-api23.p.rapidapi.com/api/trending/video"
        headers = {
            "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
            "X-RapidAPI-Host": "tiktok-api23.p.rapidapi.com"
        }
        params = {
            "page": page,
            "limit": limit,
            "period": period,
            "order_by": order_by,
            "country": country
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        videos = []
        for item in data.get('data', []):
            video = {
                'title': item.get('title', ''),
                'description': item.get('desc', ''),
                'url': item.get('video_url', ''),
                'thumbnail_url': item.get('cover', ''),
                'view_count': item.get('play_count', 0),
                'like_count': item.get('digg_count', 0),
                'published_at': datetime.fromtimestamp(item.get('create_time', 0)).isoformat(),
                'channel_name': item.get('author', {}).get('nickname', ''),
                'platform': 'tiktok',
                'music': item.get('music', {}).get('title', ''),
                'duration': item.get('duration', 0),
                'share_count': item.get('share_count', 0),
                'comment_count': item.get('comment_count', 0)
            }
            videos.append(video)

        return {
            'videos': videos,
            'total': len(videos),
            'page': page,
            'limit': limit,
            'has_more': data.get('has_more', False)
        }

    except Exception as e:
        logger.error(f"Error getting TikTok trending: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 