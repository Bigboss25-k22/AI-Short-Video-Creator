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

# @router.get("/tiktok/{keyword}")
# async def search_tiktok(
#     keyword: str, 
#     cursor: str = "0",
#     search_id: str = "0"
# ):
#     """
#     Tìm kiếm video trên TikTok sử dụng RapidAPI
#     """
#     try:
#         settings = get_settings()
        
#         # Gọi TikTok API thông qua RapidAPI
#         url = "https://tiktok-api23.p.rapidapi.com/api/search/general"
#         headers = {
#             "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
#             "X-RapidAPI-Host": "tiktok-api23.p.rapidapi.com"
#         }
#         params = {
#             "keyword": keyword,
#             "cursor": cursor,
#             "search_id": search_id
#         }
        
#         response = requests.get(url, headers=headers, params=params)
        
#         # Kiểm tra lỗi chi tiết
#         if response.status_code == 403:
#             logger.error("TikTok API access forbidden. Please check your API key and subscription status.")
#             raise HTTPException(
#                 status_code=403,
#                 detail="Access to TikTok API is forbidden. Please check your API key and subscription status."
#             )
#         elif response.status_code == 429:
#             logger.error("TikTok API rate limit exceeded.")
#             raise HTTPException(
#                 status_code=429,
#                 detail="TikTok API rate limit exceeded. Please try again later."
#             )
        
#         response.raise_for_status()
#         data = response.json()

#         # Xử lý dữ liệu từ response
#         videos = []
#         items = data.get('data', [])
        
#         # Kiểm tra nếu items là list
#         if isinstance(items, list):
#             for item in items:
#                 if item.get('type') == 'video':
#                     video = {
#                         'title': item.get('title', ''),
#                         'description': item.get('desc', ''),
#                         'url': item.get('video_url', ''),
#                         'thumbnail_url': item.get('cover', ''),
#                         'view_count': item.get('play_count', 0),
#                         'like_count': item.get('digg_count', 0),
#                         'published_at': datetime.fromtimestamp(item.get('create_time', 0)).isoformat(),
#                         'channel_name': item.get('author', {}).get('nickname', ''),
#                         'platform': 'tiktok',
#                         'music': item.get('music', {}).get('title', ''),
#                         'duration': item.get('duration', 0),
#                         'share_count': item.get('share_count', 0),
#                         'comment_count': item.get('comment_count', 0)
#                     }
#                     videos.append(video)

#         # Lấy cursor và search_id cho trang tiếp theo
#         next_cursor = data.get('cursor', '0')
#         next_search_id = data.get('search_id', '0')
        
#         if next_cursor == '-1':
#             next_cursor = None

#         return {
#             'videos': videos,
#             'total': len(videos),
#             'has_more': len(videos) > 0,
#             'cursor': next_cursor,
#             'search_id': next_search_id
#         }

#     except requests.exceptions.RequestException as e:
#         logger.error(f"Error calling TikTok API: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error calling TikTok API: {str(e)}"
#         )
#     except Exception as e:
#         logger.error(f"Error searching TikTok: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error searching TikTok: {str(e)}"
#         )

# @router.get("/tiktok/user/{sec_uid}")
# async def get_user_posts(
#     sec_uid: str,
#     max_results: int = 35,
#     cursor: str = "0"
# ):
#     """
#     Lấy danh sách video của một user TikTok
#     """
#     try:
#         settings = get_settings()
        
#         # Gọi TikTok API thông qua RapidAPI
#         url = "https://tiktok-api23.p.rapidapi.com/api/user/posts"
#         headers = {
#             "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
#             "X-RapidAPI-Host": "tiktok-api23.p.rapidapi.com"
#         }
#         params = {
#             "secUid": sec_uid,
#             "count": max_results,
#             "cursor": cursor
#         }
        
#         response = requests.get(url, headers=headers, params=params)
        
#         # Kiểm tra lỗi chi tiết
#         if response.status_code == 403:
#             logger.error("TikTok API access forbidden. Please check your API key and subscription status.")
#             raise HTTPException(
#                 status_code=403,
#                 detail="Access to TikTok API is forbidden. Please check your API key and subscription status."
#             )
#         elif response.status_code == 429:
#             logger.error("TikTok API rate limit exceeded.")
#             raise HTTPException(
#                 status_code=429,
#                 detail="TikTok API rate limit exceeded. Please try again later."
#             )
        
#         response.raise_for_status()
#         data = response.json()

#         # Xử lý dữ liệu từ response
#         videos = []
#         for item in data.get('data', {}).get('itemList', []):
#             video = {
#                 'title': item.get('title', ''),
#                 'description': item.get('desc', ''),
#                 'url': item.get('video_url', ''),
#                 'thumbnail_url': item.get('cover', ''),
#                 'view_count': item.get('play_count', 0),
#                 'like_count': item.get('digg_count', 0),
#                 'published_at': datetime.fromtimestamp(item.get('create_time', 0)).isoformat(),
#                 'channel_name': item.get('author', {}).get('nickname', ''),
#                 'platform': 'tiktok',
#                 'music': item.get('music', {}).get('title', ''),
#                 'duration': item.get('duration', 0),
#                 'share_count': item.get('share_count', 0),
#                 'comment_count': item.get('comment_count', 0)
#             }
#             videos.append(video)

#         # Lấy cursor cho trang tiếp theo
#         next_cursor = data.get('data', {}).get('cursor')
#         if next_cursor == '-1':
#             next_cursor = None

#         return {
#             'videos': videos,
#             'total': len(videos),
#             'has_more': data.get('data', {}).get('hasMore', False),
#             'cursor': next_cursor,
#             'extra': data.get('data', {}).get('extra', {})
#         }

#     except requests.exceptions.RequestException as e:
#         logger.error(f"Error calling TikTok API: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error calling TikTok API: {str(e)}"
#         )
#     except Exception as e:
#         logger.error(f"Error getting user posts: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error getting user posts: {str(e)}"
#         )

# @router.get("/tiktok/trending")
# async def get_tiktok_trending(
#     page: int = 1,
#     limit: int = 20,
#     period: int = 30,
#     order_by: str = "vv",
#     country: str = "US"
# ):
#     """
#     Lấy danh sách video trending trên TikTok
#     """
#     try:
#         settings = get_settings()
        
#         # Gọi TikTok API thông qua RapidAPI
#         url = "https://tiktok-api23.p.rapidapi.com/api/trending/video"
#         headers = {
#             "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
#             "X-RapidAPI-Host": "tiktok-api23.p.rapidapi.com"
#         }
#         params = {
#             "page": page,
#             "limit": limit,
#             "period": period,
#             "order_by": order_by,
#             "country": country
#         }
        
#         response = requests.get(url, headers=headers, params=params)
#         response.raise_for_status()
#         data = response.json()

#         videos = []
#         for item in data.get('data', []):
#             video = {
#                 'title': item.get('title', ''),
#                 'description': item.get('desc', ''),
#                 'url': item.get('video_url', ''),
#                 'thumbnail_url': item.get('cover', ''),
#                 'view_count': item.get('play_count', 0),
#                 'like_count': item.get('digg_count', 0),
#                 'published_at': datetime.fromtimestamp(item.get('create_time', 0)).isoformat(),
#                 'channel_name': item.get('author', {}).get('nickname', ''),
#                 'platform': 'tiktok',
#                 'music': item.get('music', {}).get('title', ''),
#                 'duration': item.get('duration', 0),
#                 'share_count': item.get('share_count', 0),
#                 'comment_count': item.get('comment_count', 0)
#             }
#             videos.append(video)

#         return {
#             'videos': videos,
#             'total': len(videos),
#             'page': page,
#             'limit': limit,
#             'has_more': data.get('has_more', False)
#         }

#     except Exception as e:
#         logger.error(f"Error getting TikTok trending: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/tiktok/trending-keywords")
# async def get_tiktok_trending_keywords(
#     limit: int = 20,
#     country: str = "US"
# ):
#     """
#     Lấy danh sách trending keywords từ TikTok
#     """
#     try:
#         settings = get_settings()
        
#         # Kiểm tra API key
#         if not settings.RAPIDAPI_KEY:
#             logger.warning("RAPIDAPI_KEY not configured, returning fallback keywords")
#             fallback_keywords = [
#                 "trending", "viral", "funny", "dance", "music", 
#                 "comedy", "food", "travel", "beauty", "fashion",
#                 "gaming", "sports", "education", "lifestyle", "entertainment"
#             ]
#             return {
#                 'keywords': fallback_keywords,
#                 'total': len(fallback_keywords),
#                 'country': country,
#                 'source': 'fallback'
#             }
        
#         # Gọi TikTok API thông qua RapidAPI để lấy trending videos
#         url = "https://tiktok-api23.p.rapidapi.com/api/trending/video"
#         headers = {
#             "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
#             "X-RapidAPI-Host": "tiktok-api23.p.rapidapi.com"
#         }
#         params = {
#             "page": 1,
#             "limit": limit,
#             "period": 7,  # 7 ngày gần đây
#             "order_by": "vv",  # Sắp xếp theo lượt xem
#             "country": country
#         }
        
#         response = requests.get(url, headers=headers, params=params, timeout=10)
        
#         # Xử lý các lỗi HTTP cụ thể
#         if response.status_code == 429:
#             logger.warning("TikTok API rate limit exceeded, using fallback keywords")
#             fallback_keywords = [
#                 "trending", "viral", "funny", "dance", "music", 
#                 "comedy", "food", "travel", "beauty", "fashion",
#                 "gaming", "sports", "education", "lifestyle", "entertainment"
#             ]
#             return {
#                 'keywords': fallback_keywords,
#                 'total': len(fallback_keywords),
#                 'country': country,
#                 'source': 'fallback',
#                 'error': 'Rate limit exceeded'
#             }
#         elif response.status_code == 403:
#             logger.warning("TikTok API access forbidden, using fallback keywords")
#             fallback_keywords = [
#                 "trending", "viral", "funny", "dance", "music", 
#                 "comedy", "food", "travel", "beauty", "fashion",
#                 "gaming", "sports", "education", "lifestyle", "entertainment"
#             ]
#             return {
#                 'keywords': fallback_keywords,
#                 'total': len(fallback_keywords),
#                 'country': country,
#                 'source': 'fallback',
#                 'error': 'Access forbidden'
#             }
        
#         response.raise_for_status()
#         data = response.json()

#         # Trích xuất keywords từ title và description của trending videos
#         keywords = set()
#         for item in data.get('data', []):
#             # Lấy từ title
#             title = item.get('title', '')
#             if title:
#                 # Tách từ title và lọc từ có độ dài > 2, loại bỏ ký tự đặc biệt
#                 title_words = [
#                     word.strip().lower() 
#                     for word in title.split() 
#                     if len(word.strip()) > 2 and word.strip().isalnum()
#                 ]
#                 keywords.update(title_words[:3])  # Lấy 3 từ đầu tiên
            
#             # Lấy từ description
#             desc = item.get('desc', '')
#             if desc:
#                 # Tách từ description và lọc từ có độ dài > 2
#                 desc_words = [
#                     word.strip().lower() 
#                     for word in desc.split() 
#                     if len(word.strip()) > 2 and word.strip().isalnum()
#                 ]
#                 keywords.update(desc_words[:2])  # Lấy 2 từ đầu tiên
            
#             # Lấy hashtags nếu có
#             hashtags = item.get('hashtags', [])
#             if hashtags:
#                 for hashtag in hashtags[:3]:  # Lấy 3 hashtag đầu tiên
#                     if hashtag.get('name'):
#                         clean_hashtag = hashtag['name'].replace('#', '').lower()
#                         if len(clean_hashtag) > 2:
#                             keywords.add(clean_hashtag)
            
#             # Giới hạn số lượng keywords
#             if len(keywords) >= 15:
#                 break

#         # Chuyển set thành list và sắp xếp theo độ dài từ ngắn đến dài
#         keywords_list = sorted(list(keywords), key=len)[:15]
        
#         # Nếu không có keywords nào, sử dụng fallback
#         if not keywords_list:
#             keywords_list = [
#                 "trending", "viral", "funny", "dance", "music", 
#                 "comedy", "food", "travel", "beauty", "fashion",
#                 "gaming", "sports", "education", "lifestyle", "entertainment"
#             ]
        
#         return {
#             'keywords': keywords_list,
#             'total': len(keywords_list),
#             'country': country,
#             'source': 'tiktok'
#         }

#     except requests.exceptions.Timeout:
#         logger.error("TikTok API request timeout")
#         fallback_keywords = [
#             "trending", "viral", "funny", "dance", "music", 
#             "comedy", "food", "travel", "beauty", "fashion",
#             "gaming", "sports", "education", "lifestyle", "entertainment"
#         ]
#         return {
#             'keywords': fallback_keywords,
#             'total': len(fallback_keywords),
#             'country': country,
#             'source': 'fallback',
#             'error': 'Request timeout'
#         }
#     except requests.exceptions.RequestException as e:
#         logger.error(f"Error calling TikTok API for trending keywords: {e}")
#         # Trả về keywords mặc định nếu API lỗi
#         fallback_keywords = [
#             "trending", "viral", "funny", "dance", "music", 
#             "comedy", "food", "travel", "beauty", "fashion",
#             "gaming", "sports", "education", "lifestyle", "entertainment"
#         ]
#         return {
#             'keywords': fallback_keywords,
#             'total': len(fallback_keywords),
#             'country': country,
#             'source': 'fallback',
#             'error': 'API request failed'
#         }
#     except Exception as e:
#         logger.error(f"Error getting TikTok trending keywords: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

@router.get("/tiktok-rapid/{keyword}")
async def search_tiktok_rapid(keyword: str, count: int = 18, cursor: int = 0):
    """
    Tìm kiếm video trên TikTok sử dụng RapidAPI (tiktok-api15.p.rapidapi.com)
    """
    settings = get_settings()
    RAPIDAPI_KEY = settings.RAPIDAPI_KEY
    if not RAPIDAPI_KEY:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY is not set in backend config")
    url = "https://tiktok-api15.p.rapidapi.com/index/Tiktok/searchVideoListByKeywords"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "tiktok-api15.p.rapidapi.com",
        "User-Agent": "RapidAPI-Playground"
    }
    params = {
        "keywords": keyword,
        "count": count,
        "cursor": cursor
    }
    try:
        logger.info(f"[TikTok RapidAPI] Request URL: {url}")
        logger.info(f"[TikTok RapidAPI] Headers: {headers}")
        logger.info(f"[TikTok RapidAPI] Params: {params}")
        response = requests.get(url, headers=headers, params=params)
        logger.info(f"[TikTok RapidAPI] Status code: {response.status_code}")
        logger.info(f"[TikTok RapidAPI] Response text: {response.text}")
        if response.status_code == 403:
            logger.error("TikTok RapidAPI access forbidden. Check your key/quota.")
            raise HTTPException(status_code=403, detail="Access to TikTok RapidAPI is forbidden. Check your key/quota.")
        elif response.status_code == 429:
            logger.error("TikTok RapidAPI rate limit exceeded.")
            raise HTTPException(status_code=429, detail="TikTok RapidAPI rate limit exceeded.")
        response.raise_for_status()
        data = response.json()
        # Chuẩn hóa dữ liệu trả về cho frontend
        videos = []
        for item in data.get('data', {}).get('videos', []):
            video = {
                'aweme_id': item.get('aweme_id', ''),
                'video_id': item.get('video_id', ''),
                'region': item.get('region', ''),
                'title': item.get('title', ''),
                'description': item.get('desc', ''),
                'cover': item.get('cover', ''),
                'ai_dynamic_cover': item.get('ai_dynamic_cover', ''),
                'origin_cover': item.get('origin_cover', ''),
                'duration': item.get('duration', 0),
                'play': item.get('play', ''),
                'wmplay': item.get('wmplay', ''),
                'hdplay': item.get('hdplay', ''),
                'size': item.get('size', 0),
                'wm_size': item.get('wm_size', 0),
                'music': item.get('music', ''),
                'music_info': item.get('music_info', {}),
                'play_count': item.get('play_count', 0),
                'digg_count': item.get('digg_count', 0),
                'comment_count': item.get('comment_count', 0),
                'share_count': item.get('share_count', 0),
                'download_count': item.get('download_count', 0),
                'create_time': item.get('create_time', 0),
                'author': {
                    'id': item.get('author', {}).get('id', ''),
                    'unique_id': item.get('author', {}).get('unique_id', ''),
                    'nickname': item.get('author', {}).get('nickname', ''),
                    'avatar': item.get('author', {}).get('avatar', ''),
                },
                'url': item.get('share_url', ''),
                'platform': 'tiktok',
            }
            videos.append(video)
        return {'videos': videos, 'total': len(videos)}
    except Exception as e:
        logger.error(f"Error searching TikTok RapidAPI: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 