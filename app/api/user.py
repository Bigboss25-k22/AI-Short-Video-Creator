from fastapi import APIRouter, Depends, HTTPException
from app.schemas.user import User, UserCreate
from app.crud.user import create_user, get_user
from app.models.user import User as UserModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from passlib.context import CryptContext
from app.common.exception.errors import CustomError
from app.common.response.response_code import CustomErrorCode

router = APIRouter(prefix="", tags=["users"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=User)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Kiểm tra trùng username/email
    if db.query(UserModel).filter_by(username=user.username).first():
        raise CustomError(CustomErrorCode.USER_ALREADY_EXISTS)
    if db.query(UserModel).filter_by(email=user.email).first():
        raise CustomError(CustomErrorCode.USER_ALREADY_EXISTS)
    # Hash password
    user_data = user.model_dump()
    user_data["password"] = pwd_context.hash(user.password)
    user_hashed = UserCreate(**user_data)
    return create_user(db, user_hashed)
