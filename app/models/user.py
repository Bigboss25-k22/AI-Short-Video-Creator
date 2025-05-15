from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from app.core.database import metadata

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), unique=True, index=True, nullable=False),
    Column("email", String(100), unique=True, index=True, nullable=False),
    Column("full_name", String(100)),
)
