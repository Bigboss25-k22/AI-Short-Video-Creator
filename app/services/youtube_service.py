from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import get_settings
import logging
from typing import List
from app.schemas.content_suggestion import VideoInfo
from datetime import datetime
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
import httpx

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.YOUTUBE_API_KEY
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
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
        
    def get_channel_videos_with_stats(self, channel_id: str, max_results: int = 20, page_token: str = None, access_token: str = None):
        """
        Lấy danh sách video của kênh kèm thống kê chi tiết từng video
        """
        try:
            # Sử dụng credentials nếu có access_token,否则 sử dụng API key
            if access_token:
                credentials = self.create_credentials(access_token)
                youtube = build('youtube', 'v3', credentials=credentials)
            else:
                youtube = self.youtube
            
            # Lấy playlist uploads của kênh
            channel_response = youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()
            
            if not channel_response['items']:
                logger.warning(f"Không tìm thấy kênh với ID: {channel_id}")
                return {'videos': [], 'next_page_token': None}
                
            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            # Lấy danh sách videoId từ playlist uploads
            playlist_items_request = youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part='contentDetails',
                maxResults=max_results,
                pageToken=page_token
            )
            playlist_items_response = playlist_items_request.execute()
            video_ids = [item['contentDetails']['videoId'] for item in playlist_items_response['items']]

            if not video_ids:
                return {'videos': [], 'next_page_token': playlist_items_response.get('nextPageToken')}

            # Lấy thông tin chi tiết từng video
            videos_response = youtube.videos().list(
                part='snippet,statistics,contentDetails,status',
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
                    'channel_name': item['snippet']['channelTitle'],
                    'privacy_status': item['status']['privacyStatus']
                }
                videos.append(video)

            next_page_token = playlist_items_response.get('nextPageToken')
            return {
                'videos': videos,
                'next_page_token': next_page_token
            }
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Không tìm thấy playlist cho kênh: {channel_id}")
                return {'videos': [], 'next_page_token': None}
            logger.error(f"HTTP Error getting channel videos: {e}")
            return {'videos': [], 'next_page_token': None}
        except Exception as e:
            logger.error(f"Error getting channel videos: {e}")
            return {'videos': [], 'next_page_token': None}

    def get_my_channel_id(self, access_token: str) -> str:
        """
        Lấy channel ID của user hiện tại
        """
        try:
            credentials = self.create_credentials(access_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            
            response = youtube.channels().list(
                part='id',
                mine=True
            ).execute()
            
            if not response['items']:
                logger.warning("Không tìm thấy kênh YouTube cho user")
                return None
                
            return response['items'][0]['id']
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning("Không tìm thấy kênh YouTube cho user")
                return None
            logger.error(f"HTTP Error getting channel ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting channel ID: {e}")
            return None

    def get_my_channel_stats(self, access_token: str):
        """
        Lấy thống kê kênh YouTube của user hiện tại
        """
        try:
            credentials = self.create_credentials(access_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            
            response = youtube.channels().list(
                part='snippet,statistics',
                mine=True
            ).execute()
            
            if not response['items']:
                logger.warning("Không tìm thấy kênh YouTube cho user")
                return None
                
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
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning("Không tìm thấy kênh YouTube cho user")
                return None
            logger.error(f"HTTP Error getting channel stats: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting channel stats: {e}")
            return None

    def get_my_videos(self, access_token: str, max_results: int = 20, page_token: str = None):
        """
        Lấy danh sách video của kênh user hiện tại
        """
        try:
            credentials = self.create_credentials(access_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Lấy channel ID của user hiện tại
            channel_response = youtube.channels().list(
                part='id',
                mine=True
            ).execute()
            
            if not channel_response['items']:
                logger.warning("Không tìm thấy kênh YouTube cho user")
                return {'videos': [], 'next_page_token': None}
                
            channel_id = channel_response['items'][0]['id']
            
            # Sử dụng method có sẵn để lấy video, truyền access_token
            return self.get_channel_videos_with_stats(channel_id, max_results, page_token, access_token)
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning("Không tìm thấy kênh YouTube cho user")
                return {'videos': [], 'next_page_token': None}
            logger.error(f"HTTP Error getting my videos: {e}")
            return {'videos': [], 'next_page_token': None}
        except Exception as e:
            logger.error(f"Error getting my videos: {e}")
            return {'videos': [], 'next_page_token': None}

    def create_credentials(self, access_token: str, refresh_token: str = None) -> Credentials:
        """
        Tạo Google Credentials object với đầy đủ thông tin
        """
        credentials_dict = {
            'token': access_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'token_uri': 'https://oauth2.googleapis.com/token'
        }
        
        if refresh_token:
            credentials_dict['refresh_token'] = refresh_token
            
        return Credentials(**credentials_dict)

    def upload_video(self, access_token: str, title: str, description: str, file_path: str, privacy_status: str = "private", refresh_token: str = None):
        """
        Đăng tải video lên YouTube
        """
        try:
            # Tạo credentials với đầy đủ thông tin
            credentials = self.create_credentials(access_token, refresh_token)
            
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
        except HttpError as e:
            error_details = e.error_details if hasattr(e, 'error_details') else []
            error_message = "Lỗi không xác định"
            
            # Xử lý các lỗi cụ thể
            for detail in error_details:
                if detail.get('reason') == 'youtubeSignupRequired':
                    error_message = "Tài khoản Google chưa có kênh YouTube. Vui lòng tạo kênh YouTube trước khi upload video."
                elif detail.get('reason') == 'quotaExceeded':
                    error_message = "Đã vượt quá giới hạn upload của YouTube API. Vui lòng thử lại sau."
                elif detail.get('reason') == 'forbidden':
                    error_message = "Không có quyền upload video. Vui lòng kiểm tra quyền truy cập YouTube."
                elif detail.get('reason') == 'invalidCredentials':
                    error_message = "Thông tin đăng nhập không hợp lệ. Vui lòng đăng nhập lại."
                elif 'Unauthorized' in str(e):
                    error_message = "Chưa đăng nhập hoặc token đã hết hạn. Vui lòng đăng nhập lại với Google."
            
            logger.error(f"YouTube upload error: {error_message} - Details: {e}")
            return {"error": error_message, "details": str(e)}
            
        except Exception as e:
            error_message = f"Lỗi upload video: {str(e)}"
            logger.error(f"Error uploading video: {e}")
            return {"error": error_message, "details": str(e)}

    def delete_video(self, access_token: str, video_id: str):
        """
        Xóa video khỏi YouTube
        """
        try:
            credentials = self.create_credentials(access_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            request = youtube.videos().delete(id=video_id)
            request.execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting video: {e}")
            return False

    def refresh_google_token(self, refresh_token: str) -> str:
        """
        Refresh Google access token sử dụng refresh token
        """
        try:
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
            
            response = httpx.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data["access_token"]
        except Exception as e:
            logger.error(f"Error refreshing Google token: {e}")
            return None 
