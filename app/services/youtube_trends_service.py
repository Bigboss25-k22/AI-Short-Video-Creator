import requests
from app.core.config import get_settings

def get_trending_keywords(region_code='VN', max_results=25):
    settings = get_settings()
    api_key = settings.YOUTUBE_API_KEY
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&chart=mostPopular&regionCode={region_code}&maxResults={max_results}&key={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"YouTube API error: {response.status_code} {response.text}")
    data = response.json()
    tags_set = set()
    for item in data.get('items', []):
        snippet = item.get('snippet', {})
        video_tags = snippet.get('tags', [])
        # Lấy 1-2 tag đầu tiên của mỗi video, ưu tiên tag chưa có trong tập hợp
        count = 0
        for tag in video_tags:
            if tag not in tags_set:
                tags_set.add(tag)
                count += 1
            if count >= 2:
                break
        if len(tags_set) >= 50:
            break
    return list(tags_set)[:50]
