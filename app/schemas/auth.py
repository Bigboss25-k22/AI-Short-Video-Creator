from pydantic import BaseModel
from typing import Optional


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AuthorizationCodeRequest(BaseModel):
    username: str
    password: str


class AuthorizationCodeResponse(BaseModel):
    code: str
