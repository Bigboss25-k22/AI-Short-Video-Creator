from fastapi import APIRouter
from app.services.youtube_trends_service import get_trending_keywords

router = APIRouter()

@router.get("/trending-keywords", summary="Lấy các tag trending từ YouTube cho khu vực VN")
def trending_keywords():
    try:
        keywords = get_trending_keywords(region_code='VN')
        return {"keywords": keywords}
    except Exception as e:
        return {"keywords": [], "error": str(e)}
