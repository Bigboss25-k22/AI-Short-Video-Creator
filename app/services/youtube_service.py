from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import get_settings
import logging
from typing import List
from app.schemas.content_suggestion import VideoInfo
from datetime import datetime, timedelta
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
import httpx
import random

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

    def get_channel_analytics(self, access_token: str, channel_id: str, time_range: str = '7d'):
        """
        Lấy dữ liệu analytics thực từ YouTube Analytics API (chỉ views và subscribers)
        """
        try:
            credentials = self.create_credentials(access_token)
            youtube_analytics = build('youtubeAnalytics', 'v2', credentials=credentials)

            end_date = datetime.now().date() - timedelta(days=1)
            if time_range == '7d':
                start_date = end_date - timedelta(days=7)
            elif time_range == '30d':
                start_date = end_date - timedelta(days=30)
            elif time_range == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=7)

            # Gọi API chỉ với metrics hợp lệ - thêm subscribersLost
            logger.info(f"Querying YouTube Analytics for channel {channel_id}, period {start_date} to {end_date}")
            response = youtube_analytics.reports().query(
                ids=f'channel=={channel_id}',
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics='views,subscribersGained,subscribersLost',
                dimensions='day',
                sort='day'
            ).execute()

            logger.info(f"YouTube Analytics response: {len(response.get('rows', []))} rows")
            if response.get('rows'):
                logger.info(f"Sample row: {response['rows'][0] if response['rows'] else 'None'}")

            # Mapping dữ liệu trả về với views, subscribers gained và lost
            analytics_data = []
            headers = [h['name'] for h in response.get('columnHeaders', [])]
            for row in response.get('rows', []):
                row_dict = dict(zip(headers, row))
                # Format ngày theo chuẩn MM/DD để hiển thị trên chart
                date_str = row_dict.get('day', '')
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        formatted_date = date_obj.strftime('%m/%d')
                    except:
                        formatted_date = date_str
                else:
                    formatted_date = ''
                
                subscribers_gained = int(row_dict.get('subscribersGained', 0))
                subscribers_lost = int(row_dict.get('subscribersLost', 0))
                net_subscribers = subscribers_gained - subscribers_lost
                    
                analytics_data.append({
                    'date': formatted_date,
                    'views': int(row_dict.get('views', 0)),
                    'subscribers': subscribers_gained,  # Subscribers gained
                    'subscribersLost': subscribers_lost,  # Subscribers lost
                    'netSubscribers': net_subscribers  # Net change (gained - lost)
                })
            return analytics_data
        except Exception as e:
            logger.error(f"YouTube Analytics API error: {e}")
            return self._generate_empty_analytics_data(time_range)

    def _generate_empty_analytics_data(self, time_range: str):
        """
        Tạo dữ liệu analytics rỗng khi không thể lấy được dữ liệu thực (views, subscribers gained/lost)
        """
        days = 7 if time_range == '7d' else 30 if time_range == '30d' else 90
        data = []
        for i in range(days - 1, -1, -1):
            date = datetime.now() - timedelta(days=i)
            data.append({
                'date': date.strftime('%m/%d'),  # Format MM/DD cho chart
                'views': 0,
                'subscribers': 0,  # Subscribers gained
                'subscribersLost': 0,  # Subscribers lost
                'netSubscribers': 0  # Net change
            })
        return data

    def get_my_channel_analytics(self, access_token: str, time_range: str = '7d'):
        """
        Lấy dữ liệu analytics của kênh người dùng hiện tại
        """
        try:
            channel_id = self.get_my_channel_id(access_token)
            if not channel_id:
                logger.warning("Không tìm thấy channel ID cho user")
                return self._generate_empty_analytics_data(time_range)
            
            return self.get_channel_analytics(access_token, channel_id, time_range)
        except Exception as e:
            logger.error(f"Error getting my channel analytics: {e}")
            return self._generate_empty_analytics_data(time_range)

    def get_video_analytics(self, access_token: str, video_id: str, time_range: str = '7d'):
        """
        Lấy dữ liệu analytics của video cụ thể
        """
        try:
            credentials = self.create_credentials(access_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Lấy thống kê cơ bản của video
            response = youtube.videos().list(
                part='statistics,snippet',
                id=video_id
            ).execute()
            
            if not response['items']:
                return None
            
            video = response['items'][0]
            stats = video['statistics']
            snippet = video['snippet']
            
            # Tạo dữ liệu analytics mẫu cho video
            return {
                'video_id': video_id,
                'title': snippet['title'],
                'published_at': snippet['publishedAt'],
                'view_count': int(stats.get('viewCount', 0)),
                'like_count': int(stats.get('likeCount', 0)),
                'comment_count': int(stats.get('commentCount', 0)),
                'analytics_data': self._generate_sample_analytics_data(time_range)
            }
            
        except Exception as e:
            logger.error(f"Error getting video analytics: {e}")
            return None

    def get_channel_demographics(self, access_token: str, channel_id: str):
        """
        Lấy dữ liệu demographics của kênh YouTube
        """
        try:
            credentials = self.create_credentials(access_token)
            
            # Sử dụng YouTube Analytics API
            try:
                youtube_analytics = build('youtubeAnalytics', 'v2', credentials=credentials)
                
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
                
                demographics_response = youtube_analytics.reports().query(
                    ids=f'channel=={channel_id}',
                    startDate=start_date.isoformat(),
                    endDate=end_date.isoformat(),
                    metrics='viewerPercentage',
                    dimensions='ageGroup,gender'
                ).execute()
                
                return demographics_response.get('rows', [])
                
            except Exception as e:
                logger.error(f"YouTube Analytics API error for demographics: {e}")
                # Trả về dữ liệu rỗng thay vì dữ liệu mẫu
                return []
                
        except Exception as e:
            logger.error(f"Error getting channel demographics: {e}")
            return []

    def get_channel_traffic_sources(self, access_token: str, channel_id: str):
        """
        Lấy dữ liệu traffic sources của kênh YouTube
        """
        try:
            credentials = self.create_credentials(access_token)
            
            # Sử dụng YouTube Analytics API
            try:
                youtube_analytics = build('youtubeAnalytics', 'v2', credentials=credentials)
                
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
                
                traffic_response = youtube_analytics.reports().query(
                    ids=f'channel=={channel_id}',
                    startDate=start_date.isoformat(),
                    endDate=end_date.isoformat(),
                    metrics='views',
                    dimensions='insightTrafficSourceDetail'
                ).execute()
                
                return traffic_response.get('rows', [])
                
            except Exception as e:
                logger.error(f"YouTube Analytics API error for traffic sources: {e}")
                # Trả về dữ liệu rỗng thay vì dữ liệu mẫu
                return []
                
        except Exception as e:
            logger.error(f"Error getting traffic sources: {e}")
            return []

    def _generate_sample_analytics_data(self, time_range: str):
        """
        Tạo dữ liệu analytics mẫu
        """
        days = 7 if time_range == '7d' else 30 if time_range == '30d' else 90
        data = []
        
        for i in range(days - 1, -1, -1):
            date = datetime.now() - timedelta(days=i)
            data.append({
                'date': date.strftime('%m/%d'),
                'views': random.randint(100, 2000),
                'subscribers': random.randint(5, 50),
                'likes': random.randint(20, 200),
                'comments': random.randint(5, 50),
                'shares': random.randint(2, 20)
            })
        
        return data

    def _generate_sample_demographics_data(self):
        """
        Tạo dữ liệu demographics mẫu
        """
        return [
            ['13-17', 'MALE', 15.5],
            ['13-17', 'FEMALE', 12.3],
            ['18-24', 'MALE', 25.8],
            ['18-24', 'FEMALE', 22.1],
            ['25-34', 'MALE', 18.7],
            ['25-34', 'FEMALE', 16.2],
            ['35-44', 'MALE', 12.4],
            ['35-44', 'FEMALE', 10.8],
            ['45-54', 'MALE', 8.3],
            ['45-54', 'FEMALE', 7.2],
            ['55-64', 'MALE', 5.1],
            ['55-64', 'FEMALE', 4.8],
            ['65+', 'MALE', 3.2],
            ['65+', 'FEMALE', 2.9]
        ]

    def _generate_sample_traffic_sources_data(self):
        """
        Tạo dữ liệu traffic sources mẫu
        """
        return [
            ['ADVERTISING', 25.5],
            ['ANNOTATION', 5.2],
            ['EXTERNAL_URL', 15.8],
            ['PLAYLIST', 12.3],
            ['PROMOTED', 8.7],
            ['SEARCH', 20.1],
            ['SUBSCRIBER', 12.4]
        ]

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

    def get_my_channel_analytics_detailed(self, access_token: str, time_range: str = '7d'):
        """
        Lấy dữ liệu analytics chi tiết của kênh người dùng hiện tại
        """
        try:
            channel_id = self.get_my_channel_id(access_token)
            if not channel_id:
                logger.warning("Không tìm thấy channel ID cho user")
                return self._generate_empty_analytics_data(time_range)
            
            return self.get_channel_analytics(access_token, channel_id, time_range)
        except Exception as e:
            logger.error(f"Error getting my channel analytics detailed: {e}")
            return self._generate_empty_analytics_data(time_range)

    def get_my_channel_analytics_summary(self, access_token: str):
        """
        Lấy tổng quan analytics của kênh người dùng hiện tại
        """
        try:
            channel_id = self.get_my_channel_id(access_token)
            if not channel_id:
                logger.warning("Không tìm thấy channel ID cho user")
                return {
                    'total_views': 0,
                    'total_likes': 0,
                    'total_comments': 0,
                    'total_watch_time': 0,
                    'total_subscribers': 0,
                    'engagement_rate': 0
                }
            
            # Lấy dữ liệu 30 ngày gần nhất
            analytics_data = self.get_channel_analytics(access_token, channel_id, '30d')
            
            if not analytics_data:
                return {
                    'total_views': 0,
                    'total_likes': 0,
                    'total_comments': 0,
                    'total_watch_time': 0,
                    'total_subscribers': 0,
                    'engagement_rate': 0
                }
            
            # Tính tổng các metrics
            total_views = sum(item.get('views', 0) for item in analytics_data)
            total_likes = sum(item.get('likes', 0) for item in analytics_data)
            total_comments = sum(item.get('comments', 0) for item in analytics_data)
            total_watch_time = sum(item.get('watchTime', 0) for item in analytics_data)
            total_subscribers = sum(item.get('subscribers', 0) for item in analytics_data)
            
            # Tính tỷ lệ tương tác
            engagement_rate = 0
            if total_views > 0:
                engagement_rate = ((total_likes + total_comments) / total_views) * 100
            
            return {
                'total_views': total_views,
                'total_likes': total_likes,
                'total_comments': total_comments,
                'total_watch_time': total_watch_time,
                'total_subscribers': total_subscribers,
                'engagement_rate': round(engagement_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting my channel analytics summary: {e}")
            return {
                'total_views': 0,
                'total_likes': 0,
                'total_comments': 0,
                'total_watch_time': 0,
                'total_subscribers': 0,
                'engagement_rate': 0
            } 

    def get_video_analytics_detailed(self, access_token: str, video_id: str, time_range: str = '7d'):
        """
        Lấy dữ liệu analytics chi tiết của video cụ thể
        """
        try:
            credentials = self.create_credentials(access_token)
            youtube_analytics = build('youtubeAnalytics', 'v2', credentials=credentials)
            
            # Lấy thống kê cơ bản của video
            youtube = build('youtube', 'v3', credentials=credentials)
            response = youtube.videos().list(
                part='statistics,snippet',
                id=video_id
            ).execute()
            
            if not response['items']:
                return None
            
            video = response['items'][0]
            stats = video['statistics']
            snippet = video['snippet']
            
            # Tính toán thời gian
            end_date = datetime.now().date() - timedelta(days=1)
            if time_range == '7d':
                start_date = end_date - timedelta(days=7)
            elif time_range == '30d':
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=7)
            
            # Lấy analytics chi tiết cho video
            try:
                analytics_response = youtube_analytics.reports().query(
                    ids=f'video=={video_id}',
                    startDate=start_date.isoformat(),
                    endDate=end_date.isoformat(),
                    metrics='views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares,favoritesAdded,favoritesRemoved',
                    dimensions='day',
                    sort='day'
                ).execute()
                
                analytics_data = []
                headers = [h['name'] for h in analytics_response.get('columnHeaders', [])]
                for row in analytics_response.get('rows', []):
                    row_dict = dict(zip(headers, row))
                    analytics_data.append({
                        'date': row_dict.get('day', ''),
                        'views': row_dict.get('views', 0),
                        'likes': row_dict.get('likes', 0),
                        'comments': row_dict.get('comments', 0),
                        'shares': row_dict.get('shares', 0),
                        'watchTime': row_dict.get('estimatedMinutesWatched', 0),
                        'averageViewDuration': row_dict.get('averageViewDuration', 0),
                        'favoritesAdded': row_dict.get('favoritesAdded', 0),
                        'favoritesRemoved': row_dict.get('favoritesRemoved', 0),
                        'engagementRate': self._calculate_engagement_rate(
                            row_dict.get('views', 0),
                            row_dict.get('likes', 0),
                            row_dict.get('comments', 0),
                            row_dict.get('shares', 0)
                        )
                    })
            except Exception as e:
                logger.warning(f"Không thể lấy analytics chi tiết cho video {video_id}: {e}")
                analytics_data = self._generate_sample_analytics_data(time_range)
            
            return {
                'video_id': video_id,
                'title': snippet['title'],
                'description': snippet.get('description', ''),
                'published_at': snippet['publishedAt'],
                'thumbnail_url': snippet['thumbnails']['high']['url'],
                'view_count': int(stats.get('viewCount', 0)),
                'like_count': int(stats.get('likeCount', 0)),
                'comment_count': int(stats.get('commentCount', 0)),
                'duration': snippet.get('duration', ''),
                'privacy_status': snippet.get('privacyStatus', ''),
                'analytics_data': analytics_data,
                'total_engagement': int(stats.get('likeCount', 0)) + int(stats.get('commentCount', 0)),
                'engagement_rate': self._calculate_engagement_rate(
                    int(stats.get('viewCount', 0)),
                    int(stats.get('likeCount', 0)),
                    int(stats.get('commentCount', 0)),
                    0  # shares không có trong basic stats
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting detailed video analytics: {e}")
            return None

    def get_channel_analytics_summary_enhanced(self, access_token: str, time_range: str = '30d'):
        """
        Lấy tổng quan analytics đơn giản của kênh (views và subscribers)
        """
        try:
            channel_id = self.get_my_channel_id(access_token)
            if not channel_id:
                logger.warning("Không tìm thấy channel ID cho user")
                return self._generate_empty_summary()
            
            credentials = self.create_credentials(access_token)
            youtube_analytics = build('youtubeAnalytics', 'v2', credentials=credentials)

            # Tính toán ngày bắt đầu và kết thúc
            end_date = datetime.now().date() - timedelta(days=1)
            if time_range == '7d':
                start_date = end_date - timedelta(days=7)
            elif time_range == '30d':
                start_date = end_date - timedelta(days=30)
            elif time_range == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)

            try:
                # Gọi YouTube Analytics API để lấy tổng views, subscribers gained và lost
                logger.info(f"Querying YouTube Analytics summary for channel {channel_id}, period {start_date} to {end_date}")
                response = youtube_analytics.reports().query(
                    ids=f'channel=={channel_id}',
                    startDate=start_date.isoformat(),
                    endDate=end_date.isoformat(),
                    metrics='views,subscribersGained,subscribersLost'
                ).execute()

                logger.info(f"YouTube Analytics summary response: {response}")

                total_views = 0
                total_subscribers_gained = 0
                total_subscribers_lost = 0
                
                if response.get('rows'):
                    # Lấy tổng từ kết quả API
                    for row in response['rows']:
                        total_views += row[0] if len(row) > 0 else 0
                        total_subscribers_gained += row[1] if len(row) > 1 else 0
                        total_subscribers_lost += row[2] if len(row) > 2 else 0

                logger.info(f"Calculated totals: views={total_views}, gained={total_subscribers_gained}, lost={total_subscribers_lost}")

                net_subscribers = total_subscribers_gained - total_subscribers_lost

                return {
                    'total_views': total_views,
                    'total_subscribers': total_subscribers_gained,  # Kept for backward compatibility
                    'total_subscribers_gained': total_subscribers_gained,
                    'total_subscribers_lost': total_subscribers_lost,
                    'net_subscribers': net_subscribers,
                    'time_range': time_range,
                    'data_points': len(response.get('rows', [])),
                    'best_performing_day': None
                }

            except Exception as api_error:
                logger.error(f"YouTube Analytics API error: {api_error}")
                # Fallback to empty data
                return self._generate_empty_summary()
            
        except Exception as e:
            logger.error(f"Error getting simple channel analytics summary: {e}")
            return self._generate_empty_summary()

    def _generate_empty_summary(self):
        """
        Tạo dữ liệu summary rỗng (views, subscribers gained/lost)
        """
        return {
            'total_views': 0,
            'total_subscribers': 0,  # Kept for backward compatibility
            'total_subscribers_gained': 0,
            'total_subscribers_lost': 0,
            'net_subscribers': 0,
            'time_range': '30d',
            'data_points': 0,
            'best_performing_day': None
        }

    def get_channel_analytics_by_geography(self, access_token: str, channel_id: str, time_range: str = '30d'):
        """
        Lấy dữ liệu analytics theo địa lý
        """
        try:
            credentials = self.create_credentials(access_token)
            youtube_analytics = build('youtubeAnalytics', 'v2', credentials=credentials)
            
            end_date = datetime.now().date() - timedelta(days=1)
            if time_range == '7d':
                start_date = end_date - timedelta(days=7)
            elif time_range == '30d':
                start_date = end_date - timedelta(days=30)
            elif time_range == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            response = youtube_analytics.reports().query(
                ids=f'channel=={channel_id}',
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics='views,estimatedMinutesWatched',
                dimensions='country',
                sort='-views'
            ).execute()
            
            geography_data = []
            headers = [h['name'] for h in response.get('columnHeaders', [])]
            for row in response.get('rows', []):
                row_dict = dict(zip(headers, row))
                geography_data.append({
                    'country': row_dict.get('country', 'Unknown'),
                    'views': row_dict.get('views', 0),
                    'watchTime': row_dict.get('estimatedMinutesWatched', 0)
                })
            
            return geography_data
            
        except Exception as e:
            logger.error(f"Error getting geography analytics: {e}")
            return []

    def get_channel_analytics_by_device(self, access_token: str, channel_id: str, time_range: str = '30d'):
        """
        Lấy dữ liệu analytics theo thiết bị
        """
        try:
            credentials = self.create_credentials(access_token)
            youtube_analytics = build('youtubeAnalytics', 'v2', credentials=credentials)
            
            end_date = datetime.now().date() - timedelta(days=1)
            if time_range == '7d':
                start_date = end_date - timedelta(days=7)
            elif time_range == '30d':
                start_date = end_date - timedelta(days=30)
            elif time_range == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            response = youtube_analytics.reports().query(
                ids=f'channel=={channel_id}',
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics='views,estimatedMinutesWatched',
                dimensions='deviceType',
                sort='-views'
            ).execute()
            
            device_data = []
            headers = [h['name'] for h in response.get('columnHeaders', [])]
            for row in response.get('rows', []):
                row_dict = dict(zip(headers, row))
                device_data.append({
                    'device_type': row_dict.get('deviceType', 'Unknown'),
                    'views': row_dict.get('views', 0),
                    'watchTime': row_dict.get('estimatedMinutesWatched', 0)
                })
            
            return device_data
            
        except Exception as e:
            logger.error(f"Error getting device analytics: {e}")
            return []

    def test_analytics_access(self, access_token: str):
        """
        Test YouTube Analytics API access and permissions
        """
        try:
            # First check channel eligibility
            eligibility = self.check_channel_eligibility(access_token)
            
            channel_id = self.get_my_channel_id(access_token)
            if not channel_id:
                return {
                    'success': False,
                    'error': 'No channel found',
                    'message': 'User does not have a YouTube channel',
                    'eligibility': eligibility
                }

            credentials = self.create_credentials(access_token)
            youtube_analytics = build('youtubeAnalytics', 'v2', credentials=credentials)

            # Test with a simple query for the last 7 days
            end_date = datetime.now().date() - timedelta(days=1)
            start_date = end_date - timedelta(days=7)

            logger.info(f"Testing Analytics API access for channel {channel_id}")
            logger.info(f"Channel eligibility: {eligibility}")
            
            # Try to query basic metrics
            response = youtube_analytics.reports().query(
                ids=f'channel=={channel_id}',
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics='views'
            ).execute()

            logger.info(f"Analytics API test response: {response}")

            return {
                'success': True,
                'channel_id': channel_id,
                'data_points': len(response.get('rows', [])),
                'response': response,
                'message': 'YouTube Analytics API access is working',
                'eligibility': eligibility
            }

        except HttpError as e:
            logger.error(f"YouTube Analytics API HTTP error: {e}")
            error_details = e.error_details[0] if e.error_details else {}
            
            # Get eligibility info for better error message
            try:
                eligibility = self.check_channel_eligibility(access_token)
            except:
                eligibility = {'eligible': False, 'reason': 'Unable to check'}
            
            return {
                'success': False,
                'error': f'HTTP {e.resp.status}: {error_details.get("message", str(e))}',
                'message': 'YouTube Analytics API access denied. Channel may not meet requirements (1000+ subscribers or monetization enabled).',
                'eligibility': eligibility
            }
        except Exception as e:
            logger.error(f"YouTube Analytics API test error: {e}")
            
            # Get eligibility info for better error message
            try:
                eligibility = self.check_channel_eligibility(access_token)
            except:
                eligibility = {'eligible': False, 'reason': 'Unable to check'}
                
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to test YouTube Analytics API access',
                'eligibility': eligibility
            }

    def check_channel_eligibility(self, access_token: str):
        """
        Check if channel meets YouTube Analytics API requirements
        """
        try:
            channel_stats = self.get_my_channel_stats(access_token)
            if not channel_stats:
                return {
                    'eligible': False,
                    'reason': 'No channel found',
                    'requirements_met': [],
                    'requirements_missing': ['Channel not found']
                }
            
            subscriber_count = channel_stats.get('subscriber_count', 0)
            video_count = channel_stats.get('video_count', 0)
            
            requirements_met = []
            requirements_missing = []
            
            # Check subscriber requirement (1000+)
            if subscriber_count >= 1000:
                requirements_met.append(f'✅ Subscribers: {subscriber_count:,} (≥1000)')
            else:
                requirements_missing.append(f'❌ Subscribers: {subscriber_count:,} (need 1000+)')
            
            # Check video count
            if video_count > 0:
                requirements_met.append(f'✅ Videos: {video_count}')
            else:
                requirements_missing.append(f'❌ Videos: {video_count} (need some content)')
            
            # Check channel age (approximate)
            from datetime import datetime
            published_date = datetime.fromisoformat(channel_stats.get('published_at', '').replace('Z', '+00:00'))
            channel_age_days = (datetime.now(published_date.tzinfo) - published_date).days
            
            if channel_age_days >= 30:
                requirements_met.append(f'✅ Channel age: {channel_age_days} days (≥30)')
            else:
                requirements_missing.append(f'❌ Channel age: {channel_age_days} days (need 30+)')
            
            eligible = len(requirements_missing) == 0 or subscriber_count >= 1000
            
            return {
                'eligible': eligible,
                'reason': 'Meets requirements' if eligible else 'Does not meet YouTube Analytics requirements',
                'requirements_met': requirements_met,
                'requirements_missing': requirements_missing,
                'channel_stats': channel_stats,
                'recommendations': [
                    'Get 1000+ subscribers to unlock Analytics API',
                    'Create engaging content regularly',
                    'Enable monetization when eligible',
                    'Verify channel with phone number'
                ] if not eligible else []
            }
            
        except Exception as e:
            logger.error(f"Error checking channel eligibility: {e}")
            return {
                'eligible': False,
                'reason': f'Error checking eligibility: {str(e)}',
                'requirements_met': [],
                'requirements_missing': ['Unable to check requirements']
            }