from databases import Database
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from app.core.config import settings  # Sử dụng settings từ config
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

# Cải thiện engine configuration với connection pooling
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    poolclass=QueuePool,
    pool_size=10,  # Số connection trong pool
    max_overflow=20,  # Số connection tối đa có thể tạo thêm
    pool_pre_ping=True,  # Kiểm tra connection trước khi sử dụng
    pool_recycle=3600,  # Recycle connection sau 1 giờ
    connect_args={
        "connect_timeout": 10,  # Timeout kết nối 10 giây
        "application_name": "ai-video-creator",  # Tên ứng dụng
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        # Test connection trước khi sử dụng
        db.execute("SELECT 1")
        yield db
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

database = Database(DATABASE_URL)
Base = declarative_base()
