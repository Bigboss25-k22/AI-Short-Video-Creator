from fastapi import FastAPI
from app.api import user
from app.api import auth
from app.common.exception.exception_handler import register_exception
import logging

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

app = FastAPI()
app.include_router(user.router)
app.include_router(auth.router)

register_exception(app)
