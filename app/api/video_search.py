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


def get_youtube_client():
    settings = get_settings()
    return build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)


def get_google_search_client():
    settings = get_settings()
    return build("customsearch", "v1", developerKey=settings.GOOGLE_API_KEY)


@router.get("/youtube/{keyword}")
async def search_youtube(keyword: str, max_results: int = 10):
    try:
        youtube = get_youtube_client()

        search_response = (
            youtube.search()
            .list(
                q=keyword,
                part="snippet",
                maxResults=max_results,
                type="video",
                videoDuration="short",
                order="viewCount",
            )
            .execute()
        )

        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]

        videos_response = (
            youtube.videos()
            .list(part="snippet,statistics,contentDetails", id=",".join(video_ids))
            .execute()
        )

        videos = []
        for item in videos_response.get("items", []):
            video = {
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "thumbnail_url": item["snippet"]["thumbnails"]["high"]["url"],
                "view_count": int(item["statistics"]["viewCount"]),
                "like_count": int(item["statistics"].get("likeCount", 0)),
                "published_at": item["snippet"]["publishedAt"],
                "duration": item["contentDetails"]["duration"],
                "channel_name": item["snippet"]["channelTitle"],
            }
            videos.append(video)

        return {"videos": videos, "total": len(videos)}
    except Exception as e:
        logger.error(f"Error searching YouTube: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/google/{keyword}")
async def search_google(keyword: str, max_results: int = 10):
    try:
        youtube = get_youtube_client()

        search_response = (
            youtube.search()
            .list(
                q=keyword,
                part="snippet",
                maxResults=max_results,
                type="video",
                videoDuration="short",
                order="viewCount",
            )
            .execute()
        )

        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]

        videos_response = (
            youtube.videos()
            .list(part="snippet,statistics,contentDetails", id=",".join(video_ids))
            .execute()
        )

        videos = []
        for item in videos_response.get("items", []):
            video = {
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "thumbnail_url": item["snippet"]["thumbnails"]["high"]["url"],
                "view_count": int(item["statistics"]["viewCount"]),
                "like_count": int(item["statistics"].get("likeCount", 0)),
                "published_at": item["snippet"]["publishedAt"],
                "duration": item["contentDetails"]["duration"],
                "channel_name": item["snippet"]["channelTitle"],
                "platform": "youtube",
            }
            videos.append(video)

        return {"videos": videos, "total": len(videos)}
    except Exception as e:
        logger.error(f"Error searching Google: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tiktok-rapid/{keyword}")
async def search_tiktok_rapid(keyword: str, count: int = 18, cursor: int = 0):
    """Tìm kiếm video trên TikTok sử dụng RapidAPI (tiktok-api15.p.rapidapi.com)"""
    settings = get_settings()
    RAPIDAPI_KEY = settings.RAPIDAPI_KEY
    if not RAPIDAPI_KEY:
        raise HTTPException(
            status_code=500, detail="RAPIDAPI_KEY is not set in backend config"
        )
    url = "https://tiktok-api15.p.rapidapi.com/index/Tiktok/searchVideoListByKeywords"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "tiktok-api15.p.rapidapi.com",
        "User-Agent": "RapidAPI-Playground",
    }
    params = {"keywords": keyword, "count": count, "cursor": cursor}
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 403:
            logger.error("TikTok RapidAPI access forbidden. Check your key/quota.")
            raise HTTPException(
                status_code=403,
                detail="Access to TikTok RapidAPI is forbidden. Check your key/quota.",
            )
        elif response.status_code == 429:
            logger.error("TikTok RapidAPI rate limit exceeded.")
            raise HTTPException(
                status_code=429, detail="TikTok RapidAPI rate limit exceeded."
            )
        response.raise_for_status()
        data = response.json()
        videos = []
        for item in data.get("data", {}).get("videos", []):
            video = {
                "aweme_id": item.get("aweme_id", ""),
                "video_id": item.get("video_id", ""),
                "region": item.get("region", ""),
                "title": item.get("title", ""),
                "description": item.get("desc", ""),
                "cover": item.get("cover", ""),
                "ai_dynamic_cover": item.get("ai_dynamic_cover", ""),
                "origin_cover": item.get("origin_cover", ""),
                "duration": item.get("duration", 0),
                "play": item.get("play", ""),
                "wmplay": item.get("wmplay", ""),
                "hdplay": item.get("hdplay", ""),
                "size": item.get("size", 0),
                "wm_size": item.get("wm_size", 0),
                "music": item.get("music", ""),
                "music_info": item.get("music_info", {}),
                "play_count": item.get("play_count", 0),
                "digg_count": item.get("digg_count", 0),
                "comment_count": item.get("comment_count", 0),
                "share_count": item.get("share_count", 0),
                "download_count": item.get("download_count", 0),
                "create_time": item.get("create_time", 0),
                "author": {
                    "id": item.get("author", {}).get("id", ""),
                    "unique_id": item.get("author", {}).get("unique_id", ""),
                    "nickname": item.get("author", {}).get("nickname", ""),
                    "avatar": item.get("author", {}).get("avatar", ""),
                },
                "url": item.get("share_url", ""),
                "platform": "tiktok",
            }
            videos.append(video)
        return {"videos": videos, "total": len(videos)}
    except Exception as e:
        logger.error(f"Error searching TikTok RapidAPI: {e}")
        raise HTTPException(status_code=500, detail=str(e))
