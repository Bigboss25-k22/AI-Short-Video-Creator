import httpx
from app.core.config import settings
from app.schemas.auth import GoogleUserInfo
from app.core.auth import create_access_token, create_refresh_token
from datetime import datetime, timedelta, timezone
from app.crud.token import save_refresh_token
from sqlalchemy.orm import Session
from app.models.user import User
from passlib.context import CryptContext
from fastapi import HTTPException, status

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class GoogleAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

    async def get_access_token(self, code: str) -> str:
        """Lấy access token từ Google OAuth2"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                        "grant_type": "authorization_code"
                    }
                )
                response.raise_for_status()
                return response.json()["access_token"]
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json() if e.response.content else str(e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get access token from Google: {error_detail}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error getting access token: {str(e)}"
            )

    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """Lấy thông tin người dùng từ Google"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                return GoogleUserInfo(**response.json())
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json() if e.response.content else str(e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get user info from Google: {error_detail}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error getting user info: {str(e)}"
            )

    def get_or_create_user(self, db: Session, user_info: GoogleUserInfo) -> User:
        """Lấy hoặc tạo user từ thông tin Google"""
        try:
            user = db.query(User).filter(User.email == user_info.email).first()
            
            if not user:
                # Tạo user mới nếu chưa tồn tại
                user = User(
                    email=user_info.email,
                    username=user_info.email.split('@')[0],  # Sử dụng phần trước @ của email làm username
                    full_name=user_info.name,
                    hashed_password=pwd_context.hash("google_oauth2"),  # Mật khẩu mặc định
                    role="user",
                    avatar_url=user_info.picture,
                    is_google_user=True,
                    is_active=True  # Set is_active cho user mới
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            
            return user
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error creating/getting user: {str(e)}"
            )

    def create_tokens(self, db: Session, user: User) -> dict:
        """Tạo access token và refresh token"""
        try:
            access_token = create_access_token({
                "sub": user.username,
                "role": user.role
            })
            refresh_token = create_refresh_token({"sub": user.username})
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            
            # Lưu refresh token
            save_refresh_token(db, refresh_token, user.id, expires_at)
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error creating tokens: {str(e)}"
            ) 