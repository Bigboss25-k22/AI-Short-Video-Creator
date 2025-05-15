# 6. api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from models.user import User
from schemas.auth import TokenResponse, RefreshTokenRequest
from core.auth import create_access_token, create_refresh_token, decode_token
from core.database import get_db
from crud.token import save_refresh_token, delete_refresh_token, get_refresh_token
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(User).filter_by(username=form_data.username).first()
    if not user or not form_data.password == "test":  # Thay bằng verify_password
        raise HTTPException(status_code=401, detail="Sai thông tin đăng nhập")

    access_token = create_access_token({"sub": user.username, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.username})
    expires_at = datetime.utcnow() + timedelta(days=7)

    save_refresh_token(db, refresh_token, user.id, expires_at)

    return {"access_token": access_token, "refresh_token": refresh_token}


@router.post("/refresh-token", response_model=TokenResponse)
def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    db_token = get_refresh_token(db, body.refresh_token)
    if not db_token or db_token.expires_at < datetime.utcnow():
        if db_token:
            delete_refresh_token(db, body.refresh_token)
        raise HTTPException(status_code=401, detail="Token hết hạn hoặc không hợp lệ")

    user = db_token.user
    delete_refresh_token(db, body.refresh_token)

    new_refresh_token = create_refresh_token({"sub": user.username})
    new_expires_at = datetime.utcnow() + timedelta(days=7)
    save_refresh_token(db, new_refresh_token, user.id, new_expires_at)

    new_access_token = create_access_token({"sub": user.username, "role": user.role})

    return {"access_token": new_access_token, "refresh_token": new_refresh_token}


@router.post("/logout")
def logout(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    delete_refresh_token(db, body.refresh_token)
    return {"msg": "Logged out"}
