from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import User as UserSchema, UserUpdate
from app.core.database import get_db
from app.core.auth import decode_token
from app.crud.token import get_refresh_token, delete_refresh_token
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from typing import Optional
from datetime import datetime, timezone


# Dependency lấy user hiện tại từ token
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    access_token = request.cookies.get("access_token")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực người dùng",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if refresh_token:
        try:
            db_token = get_refresh_token(db, refresh_token)
            if not db_token or db_token.expires_at < datetime.now(timezone.utc):
                if db_token:
                    delete_refresh_token(db, refresh_token)
                raise credentials_exception

            user = db_token.user
            if user is None:
                raise credentials_exception
            return user

        except Exception:

            if access_token:
                pass
            else:
                raise credentials_exception

    if access_token:
        try:
            payload = decode_token(access_token)
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except Exception:
            raise credentials_exception

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception
        return user

    raise credentials_exception


router = APIRouter(
    prefix="/users", tags=["users"], dependencies=[Depends(get_current_user)]
)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user hiện tại"""
    return current_user


@router.put("/me", response_model=UserSchema)
async def update_user_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cập nhật thông tin user hiện tại"""
    current_user.full_name = user_update.full_name
    current_user.email = user_update.email
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    old_password: str = Body(...),
    new_password: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Đổi mật khẩu cho user hiện tại"""
    if not pwd_context.verify(old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mật khẩu cũ không đúng")
    current_user.hashed_password = pwd_context.hash(new_password)
    db.commit()
    return {"msg": "Đổi mật khẩu thành công"}
