from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router, storage as storage_api
from app.core.config import get_settings
from app.common.exception.exception_handler import register_exception
from app.core.logging import setup_logging
from app.core.database import SessionLocal
import uvicorn
import asyncio
import signal
import sys
from starlette.middleware.base import BaseHTTPMiddleware

# Thiết lập logging
setup_logging()

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Đúng domain FE, KHÔNG ĐƯỢC LÀ "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Đăng ký các router
app.include_router(api_router, prefix="/api")
app.include_router(storage_api.router, prefix="/api/v1/storage", tags=["Storage"])

class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.db = SessionLocal()
        try:
            response = await call_next(request)
        finally:
            request.state.db.close()
        return response

app.add_middleware(DBSessionMiddleware)

@app.get("/")
async def root():
    return {"message": "Welcome to Architecture Design API"}

# Đăng ký exception handler
register_exception(app)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\nReceived signal {signum}. Shutting down gracefully...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configure asyncio to handle cancellation better
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Disable reload to avoid a2wsgi import issue
            log_level="info",
            access_log=False  # Disable access logs to reduce noise
        )
    except KeyboardInterrupt:
        print("\nServer shutdown gracefully")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        print("Server stopped")