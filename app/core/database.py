from databases import Database
from sqlalchemy import create_engine, MetaData
from dotenv import load_dotenv
import os

# Chỉ định rõ đường dẫn tới file .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

database = Database(DATABASE_URL)  # <-- Sửa dòng này
engine = create_engine(DATABASE_URL, echo=True)
metadata = MetaData()
