from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import get_settings
import logging
from typing import List
from app.schemas.content_suggestion import VideoInfo
from datetime import datetime

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.YOUTUBE_API_KEY
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY is not set in settings")
        
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def search_videos(self, keyword: str, max_results: int = 10) -> List[VideoInfo]:
        """
        Tìm kiếm video trên YouTube theo từ khóa
        """
        try:
            # Tìm kiếm video
            search_response = self.youtube.search().list(
                q=keyword,
                part='snippet',
                maxResults=max_results,
                type='video',
                videoDuration='short',  # Chỉ lấy video ngắn
                order='viewCount'  # Sắp xếp theo lượt xem
            ).execute()

            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            
            # Lấy thông tin chi tiết của video
            videos_response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute()

            videos = []
            for item in videos_response.get('items', []):
                video = VideoInfo(
                    title=item['snippet']['title'],
                    description=item['snippet']['description'],
                    url=f"https://www.youtube.com/watch?v={item['id']}",
                    thumbnail_url=item['snippet']['thumbnails']['high']['url'],
                    view_count=int(item['statistics']['viewCount']),
                    like_count=int(item['statistics'].get('likeCount', 0)),
                    published_at=datetime.strptime(item['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'),
                    platform="youtube",
                    duration=item['contentDetails']['duration'],
                    channel_name=item['snippet']['channelTitle']
                )
                videos.append(video)

            return videos

        except HttpError as e:
            logger.error(f"An HTTP error occurred: {e}")
            return []
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return [] 