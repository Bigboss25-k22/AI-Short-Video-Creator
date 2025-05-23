import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    # Tạo thư mục logs nếu chưa tồn tại
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Cấu hình logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                filename=os.path.join(log_dir, "app.log"),
                maxBytes=10485760,  # 10MB
                backupCount=5,
                encoding='utf-8'
            ),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Cấu hình logging cho các thư viện bên ngoài
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    # Cấu hình encoding cho stdout
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8') 