from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import User as UserSchema, UserUpdate
from app.core.database import get_db
from app.core.auth import decode_token
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from typing import Optional

# Dependency lấy user hiện tại từ token
async def get_current_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/login")), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực người dùng",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)]
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):
    """Đổi mật khẩu cho user hiện tại"""
    if not pwd_context.verify(old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mật khẩu cũ không đúng")
    current_user.hashed_password = pwd_context.hash(new_password)
    db.commit()
    return {"msg": "Đổi mật khẩu thành công"} 