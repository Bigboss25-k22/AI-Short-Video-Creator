from fastapi import FastAPI
from app.api import user
from app.api import auth

app = FastAPI()
app.include_router(user.router)
app.include_router(auth.router)
