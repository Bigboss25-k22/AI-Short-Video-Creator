from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

class Settings(BaseSettings):
    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_MINUTES: int

    # Database settings
    DATABASE_URL: str

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # DeepSeek Configuration
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

    # Zalo AI Configuration
    ZALO_AI_API_KEY: str = os.getenv("ZALO_AI_API_KEY", "")

    # Google TTS Configuration
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    # Replicate Configuration
    REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")
    REPLICATE_MODEL_ID: str = os.getenv("REPLICATE_MODEL_ID", "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b")

    # YouTube API Configuration
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")

    # TikTok API Configuration (RapidAPI)
    RAPIDAPI_KEY: str = os.getenv("RAPIDAPI_KEY", "")

    # Google Custom Search API Configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_SEARCH_ENGINE_ID: str = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")

    # Application Configuration
    APP_NAME: str = "Architecture Design API"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    APP_ENV: str = os.getenv("APP_ENV", "development")

    class Config:
        env_file = "app/.env"  # Đường dẫn tới file .env trong thư mục app
        case_sensitive = True
        extra = "allow"  # Cho phép các trường thêm vào

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
