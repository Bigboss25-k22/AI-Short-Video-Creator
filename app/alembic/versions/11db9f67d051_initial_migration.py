"""initial_migration

Revision ID: 11db9f67d051
Revises: 
Create Date: 2024-03-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '11db9f67d051'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tạo bảng users
    op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255)),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # Tạo bảng refresh_tokens
    op.create_table('refresh_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )

    # Tạo bảng video_scripts
    op.create_table('video_scripts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('creator_id', sa.String(length=36)),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('target_audience', sa.String(length=255)),
        sa.Column('total_duration', sa.Integer()),
        sa.Column('status', sa.String(length=20), server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Tạo bảng scenes
    op.create_table('scenes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('script_id', sa.String(length=36), nullable=False),
        sa.Column('scene_number', sa.Integer()),
        sa.Column('description', sa.Text()),
        sa.Column('duration', sa.Integer()),
        sa.Column('visual_elements', sa.Text()),
        sa.Column('background_music', sa.String(length=255)),
        sa.Column('voice_over', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['script_id'], ['video_scripts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Tạo bảng voice_audios
    op.create_table('voice_audios',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('script_id', sa.String(length=36), nullable=False),
        sa.Column('scene_id', sa.String(length=36), nullable=False),
        sa.Column('audio_url', sa.Text()),
        sa.Column('text_content', sa.Text()),
        sa.Column('voice_id', sa.String(length=20)),
        sa.Column('speed', sa.Float()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ),
        sa.ForeignKeyConstraint(['script_id'], ['video_scripts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Tạo bảng scene_images
    op.create_table('scene_images',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('scene_id', sa.String(length=36), nullable=False),
        sa.Column('image_url', sa.Text()),
        sa.Column('prompt', sa.Text()),
        sa.Column('width', sa.Integer(), server_default='1024'),
        sa.Column('height', sa.Integer(), server_default='768'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Xóa các bảng theo thứ tự ngược lại
    op.drop_table('scene_images')
    op.drop_table('voice_audios')
    op.drop_table('scenes')
    op.drop_table('video_scripts')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
