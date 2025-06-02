import requests
from typing import List
from app.core.config import get_settings
import logging
from app.schemas.content_suggestion import VideoInfo
from datetime import datetime

logger = logging.getLogger(__name__)

class TikTokService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.TIKTOK_API_KEY
        if not self.api_key:
            raise ValueError("TIKTOK_API_KEY is not set in settings")
        
        self.base_url = "https://api.tiktok.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def search_videos(self, keyword: str, max_results: int = 10) -> List[VideoInfo]:
        """
        Tìm kiếm video trên TikTok theo từ khóa
        """
        try:
            # Gọi API tìm kiếm TikTok
            response = requests.get(
                f"{self.base_url}/search/video",
                headers=self.headers,
                params={
                    "keyword": keyword,
                    "count": max_results,
                    "sort": "popular"  # Sắp xếp theo độ phổ biến
                }
            )
            response.raise_for_status()
            data = response.json()

            videos = []
            for item in data.get('videos', []):
                video = VideoInfo(
                    title=item.get('title', ''),
                    description=item.get('desc', ''),
                    url=item.get('video_url', ''),
                    thumbnail_url=item.get('cover_url', ''),
                    view_count=item.get('play_count', 0),
                    like_count=item.get('digg_count', 0),
                    published_at=datetime.fromtimestamp(item.get('create_time', 0)),
                    platform="tiktok",
                    duration=str(item.get('duration', 0)),
                    channel_name=item.get('author', {}).get('nickname', '')
                )
                videos.append(video)

            return videos

        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while calling TikTok API: {e}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return [] 