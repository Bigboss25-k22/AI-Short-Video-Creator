from databases import Database
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from app.core.config import settings  # Sử dụng settings từ config

DATABASE_URL = settings.DATABASE_URL
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

database = Database(DATABASE_URL)
engine = create_engine(DATABASE_URL, echo=True)
Base = declarative_base()
