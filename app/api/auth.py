# 6. api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user import User
from app.schemas.auth import TokenResponse, RefreshTokenRequest, GoogleAuthRequest
from app.schemas.user import UserCreate, User as UserSchema
from app.core.auth import create_access_token, create_refresh_token
from app.core.database import get_db
from app.crud.token import save_refresh_token, delete_refresh_token
from app.services.google_auth_service import GoogleAuthService
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="", tags=["auth"])
google_auth_service = GoogleAuthService()


@router.post("/register", response_model=UserSchema)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Đăng ký tài khoản mới"""
    # Kiểm tra username đã tồn tại
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username đã tồn tại"
        )
    
    # Kiểm tra email đã tồn tại
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã tồn tại"
        )
    
    # Tạo user mới
    hashed_password = pwd_context.hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role="user"  # Mặc định là user
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Đăng nhập và lấy access token + refresh token"""
    user = db.query(User).filter_by(username=form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai thông tin đăng nhập"
        )

    # Tạo tokens
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


@router.post("/logout")
async def logout(
    body: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Đăng xuất và vô hiệu hóa refresh token"""
    delete_refresh_token(db, body.refresh_token)
    return {"msg": "Logged out successfully"}


@router.get("/google/login")
async def google_login():
    """Tạo URL đăng nhập Google OAuth2"""
    return {
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={google_auth_service.client_id}&"
        f"redirect_uri={google_auth_service.redirect_uri}&"
        f"response_type=code&"
        f"scope=email profile&"
        f"access_type=offline"
    }

@router.get("/google/callback", response_model=TokenResponse)
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    db: Session = Depends(get_db)
):
    """Xử lý callback từ Google OAuth2"""
    try:
        # Lấy access token từ Google
        access_token = await google_auth_service.get_access_token(code)
        
        # Lấy thông tin người dùng từ Google
        user_info = await google_auth_service.get_user_info(access_token)
        
        # Lấy hoặc tạo user
        user = google_auth_service.get_or_create_user(db, user_info)
        
        # Tạo tokens
        tokens = google_auth_service.create_tokens(db, user)
        
        return tokens
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
