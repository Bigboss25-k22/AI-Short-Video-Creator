from databases import Database
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from app.core.config import settings  # Sử dụng settings từ config
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = settings.DATABASE_URL
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


database = Database(DATABASE_URL)
Base = declarative_base()
