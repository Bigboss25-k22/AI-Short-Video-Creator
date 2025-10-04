from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user import User
from app.schemas.auth import TokenResponse, RefreshTokenRequest, GoogleAuthRequest
from app.schemas.user import UserCreate, User as UserSchema
from app.core.auth import create_access_token, create_refresh_token
from app.core.database import get_db
from app.crud.token import save_refresh_token, delete_refresh_token, get_refresh_token
from app.services.google_auth_service import GoogleAuthService
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from fastapi.responses import RedirectResponse, JSONResponse


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="", tags=["auth"])
google_auth_service = GoogleAuthService()


@router.post("/register", response_model=UserSchema)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Đăng ký tài khoản mới"""
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username đã tồn tại"
        )

    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email đã tồn tại"
        )

    hashed_password = pwd_context.hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role="user",  # Mặc định là user
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Đăng nhập và lấy access token + refresh token"""
    user = db.query(User).filter_by(username=form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai thông tin đăng nhập"
        )

    access_token = create_access_token({"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.username})
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    save_refresh_token(db, refresh_token, user.id, expires_at)

    response = JSONResponse(content={"msg": "Login successful"})

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return response


@router.post("/refresh")
async def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token bằng refresh token"""
    try:
        db_token = get_refresh_token(db, body.refresh_token)
        if not db_token or db_token.expires_at < datetime.now(timezone.utc):
            if db_token:
                delete_refresh_token(db, body.refresh_token)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token không hợp lệ hoặc đã hết hạn",
            )

        user = db_token.user

        new_access_token = create_access_token(
            {"sub": user.username, "role": user.role}
        )

        return {"access_token": new_access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Không thể refresh token"
        )


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token found")
    delete_refresh_token(db, refresh_token)
    response = JSONResponse(content={"msg": "Logged out successfully"})

    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return response


@router.get("/google/login")
async def google_login():
    """Tạo URL đăng nhập Google OAuth2"""
    return {"url": google_auth_service.get_auth_url()}


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    db: Session = Depends(get_db),
):
    try:

        google_tokens = await google_auth_service.get_access_token(code)

        user_info = await google_auth_service.get_user_info(
            google_tokens["access_token"]
        )

        user = google_auth_service.get_or_create_user(db, user_info)

        tokens = google_auth_service.create_tokens(db, user)

        response = RedirectResponse(url="http://localhost:3000/explore")

        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            httponly=True,
            secure=False,
            samesite="lax",
        )
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=False,
            samesite="lax",
        )

        response.set_cookie(
            key="google_access_token",
            value=google_tokens["access_token"],
            httponly=True,
            secure=False,
            samesite="lax",
        )
        if google_tokens.get("refresh_token"):
            response.set_cookie(
                key="google_refresh_token",
                value=google_tokens["refresh_token"],
                httponly=True,
                secure=False,
                samesite="lax",
            )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}",
        )
