from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_MINUTES: int

    # Database settings
    DATABASE_URL: str

    class Config:
        env_file = "app/.env"  # Đường dẫn tới file .env trong thư mục app


settings = Settings()
