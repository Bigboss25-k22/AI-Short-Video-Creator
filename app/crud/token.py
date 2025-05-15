from models.token import RefreshToken
from sqlalchemy.orm import Session
from datetime import datetime


def save_refresh_token(db: Session, token: str, user_id: int, expires_at):
    db_token = RefreshToken(token=token, user_id=user_id, expires_at=expires_at)
    db.add(db_token)
    db.commit()
    return db_token


def delete_refresh_token(db: Session, token: str):
    db_token = db.query(RefreshToken).filter_by(token=token).first()
    if db_token:
        db.delete(db_token)
        db.commit()


def get_refresh_token(db: Session, token: str):
    return db.query(RefreshToken).filter_by(token=token).first()
