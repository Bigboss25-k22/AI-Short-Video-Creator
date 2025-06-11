from pydantic import BaseModel
from typing import Optional


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AuthorizationCodeRequest(BaseModel):
    username: str
    password: str


class AuthorizationCodeResponse(BaseModel):
    code: str


class GoogleAuthRequest(BaseModel):
    code: str


class GoogleUserInfo(BaseModel):
    email: str
    name: str
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
