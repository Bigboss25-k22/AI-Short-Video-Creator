from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import get_settings
import logging
from typing import List
from app.schemas.content_suggestion import VideoInfo
from datetime import datetime
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

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

    def get_channel_videos_with_stats(self, channel_id: str, max_results: int = 20, page_token: str = None):
        """
        Lấy danh sách video của kênh kèm thống kê chi tiết từng video
        """
        try:
            # Lấy playlist uploads của kênh
            channel_response = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()
            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            # Lấy danh sách videoId từ playlist uploads
            playlist_items_request = self.youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part='contentDetails',
                maxResults=max_results,
                pageToken=page_token
            )
            playlist_items_response = playlist_items_request.execute()
            video_ids = [item['contentDetails']['videoId'] for item in playlist_items_response['items']]

            # Lấy thông tin chi tiết từng video
            videos_response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute()

            videos = []
            for item in videos_response.get('items', []):
                video = {
                    'video_id': item['id'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'url': f"https://www.youtube.com/watch?v={item['id']}",
                    'thumbnail_url': item['snippet']['thumbnails']['high']['url'],
                    'view_count': int(item['statistics'].get('viewCount', 0)),
                    'like_count': int(item['statistics'].get('likeCount', 0)),
                    'comment_count': int(item['statistics'].get('commentCount', 0)),
                    'published_at': item['snippet']['publishedAt'],
                    'duration': item['contentDetails']['duration'],
                    'channel_name': item['snippet']['channelTitle']
                }
                videos.append(video)

            next_page_token = playlist_items_response.get('nextPageToken')
            return {
                'videos': videos,
                'next_page_token': next_page_token
            }
        except Exception as e:
            logger.error(f"Error getting channel videos: {e}")
            return {'videos': [], 'next_page_token': None}

    def upload_video(self, access_token: str, title: str, description: str, file_path: str, privacy_status: str = "private"):
        """
        Đăng tải video lên YouTube
        """
        try:
            credentials = Credentials(token=access_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                },
                'status': {
                    'privacyStatus': privacy_status
                }
            }
            media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            response = request.execute()
            return response
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            return None

    def delete_video(self, access_token: str, video_id: str):
        """
        Xóa video khỏi YouTube
        """
        try:
            credentials = Credentials(token=access_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            request = youtube.videos().delete(id=video_id)
            request.execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting video: {e}")
            return False 