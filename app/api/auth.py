# 6. api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user import User
from app.schemas.auth import TokenResponse, RefreshTokenRequest
from app.schemas.user import UserCreate, User as UserSchema
from app.core.auth import create_access_token, create_refresh_token
from app.core.database import get_db
from app.crud.token import save_refresh_token, delete_refresh_token
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="", tags=["auth"])


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
