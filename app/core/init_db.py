from app.core.database import engine, metadata
from app.models import user  # Đảm bảo import model

metadata.create_all(engine)
