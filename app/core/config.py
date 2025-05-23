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
