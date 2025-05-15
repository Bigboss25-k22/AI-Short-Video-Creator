# app/common/response/response_code.py
class StandardResponseCode:
    HTTP_200 = 200
    HTTP_400 = 400
    HTTP_401 = 401
    HTTP_403 = 403
    HTTP_404 = 404
    HTTP_422 = 422
    HTTP_500 = 500
    HTTP_502 = 502


class CustomResponseCode:
    HTTP_400 = {"code": 400, "msg": "Bad Request"}
    HTTP_401 = {"code": 401, "msg": "Unauthorized"}
    HTTP_403 = {"code": 403, "msg": "Forbidden"}
    HTTP_404 = {"code": 404, "msg": "Not Found"}
    HTTP_500 = {"code": 500, "msg": "Internal Server Error"}
    HTTP_502 = {"code": 502, "msg": "Bad Gateway"}


class CustomErrorCode:
    INVALID_CREDENTIALS = {"code": 1001, "msg": "Invalid username or password"}
    USER_ALREADY_EXISTS = {"code": 1002, "msg": "User already exists"}
    TOKEN_EXPIRED = {"code": 1003, "msg": "Token has expired"}
