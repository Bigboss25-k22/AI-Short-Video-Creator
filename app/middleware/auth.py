from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.auth import decode_token, create_access_token
from app.crud.token import get_refresh_token, save_refresh_token, delete_refresh_token
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import jwt
from functools import wraps

security = HTTPBearer()

class AuthMiddleware:
    def __init__(self, required_roles: Optional[List[str]] = None):
        self.required_roles = required_roles or []

    async def __call__(self, request: Request, call_next):
        try:
            # Lấy access token từ header
            auth = await security(request)
            access_token = auth.credentials

            try:
                # Verify và decode access token
                payload = decode_token(access_token)
                request.state.user = payload
                
                # Kiểm tra role nếu có yêu cầu
                if self.required_roles and payload.get("role") not in self.required_roles:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Không có quyền truy cập"
                    )
                
                # Forward request tới API
                response = await call_next(request)
                return response

            except jwt.ExpiredSignatureError:
                # Access token hết hạn, thử refresh
                refresh_token = request.headers.get("X-Refresh-Token")
                if not refresh_token:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Access token hết hạn và không có refresh token"
                    )

                # Verify refresh token
                db_token = get_refresh_token(request.state.db, refresh_token)
                if not db_token or db_token.expires_at < datetime.now(timezone.utc):
                    if db_token:
                        delete_refresh_token(request.state.db, refresh_token)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token không hợp lệ hoặc đã hết hạn"
                    )

                # Tạo access token mới
                user = db_token.user
                new_access_token = create_access_token({
                    "sub": user.username,
                    "role": user.role
                })

                # Forward request với access token mới
                request.headers.__dict__["_list"].append(
                    (b"authorization", f"Bearer {new_access_token}".encode())
                )
                response = await call_next(request)

                # Thêm access token mới vào response header
                response.headers["X-New-Access-Token"] = new_access_token
                return response

            except jwt.InvalidTokenError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token không hợp lệ"
                )

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


def require_auth(required_roles: Optional[List[str]] = None):
    """Decorator để yêu cầu authentication và authorization"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Không tìm thấy request object"
                )

            middleware = AuthMiddleware(required_roles)
            return await middleware(request, lambda r: func(*args, **kwargs))
        return wrapper
    return decorator 