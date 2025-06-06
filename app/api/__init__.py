from fastapi import APIRouter
from app.api import user, auth, video_script, voice, image, video_search, project_manager

api_router = APIRouter()
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(video_script.router, prefix="/video-scripts", tags=["video-scripts"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(image.router, prefix="/images", tags=["images"])
api_router.include_router(video_search.router, prefix="/search", tags=["search"])
api_router.include_router(project_manager.router, prefix="/project-manager", tags=["project-manager"]) 