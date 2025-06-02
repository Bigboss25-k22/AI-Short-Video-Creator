from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class VideoInfo(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    published_at: Optional[datetime] = None
    platform: str  # "youtube", "tiktok", "google"
    duration: Optional[str] = None
    channel_name: Optional[str] = None

class SearchRequest(BaseModel):
    keyword: str
    max_results: Optional[int] = 10

class SearchResponse(BaseModel):
    videos: List[VideoInfo]
    total_results: int 