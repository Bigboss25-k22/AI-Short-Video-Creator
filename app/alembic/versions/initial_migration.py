"""initial migration

Revision ID: initial_migration
Revises: 
Create Date: 2024-06-11 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial_migration'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Tạo bảng users trước
    op.create_table('users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=False, server_default='user'),
        sa.Column('is_google_user', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )

    # Tạo bảng refresh_tokens sau
    op.create_table('refresh_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('token')
    )

    # Tạo bảng video_scripts
    op.create_table('video_scripts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('creator_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='CASCADE')
    )

    # Tạo bảng scenes
    op.create_table('scenes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('script_id', sa.String(36), nullable=False),
        sa.Column('scene_number', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('voice_over', sa.String(), nullable=True),
        sa.Column('voice_status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('image_status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['script_id'], ['video_scripts.id'], ondelete='CASCADE')
    )

    # Tạo bảng voice_audios
    op.create_table('voice_audios',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('scene_id', sa.String(36), nullable=False),
        sa.Column('audio_base64', sa.Text(), nullable=False),
        sa.Column('text_content', sa.String(), nullable=False),
        sa.Column('voice_id', sa.String(), nullable=False),
        sa.Column('speed', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('status', sa.String(), nullable=False, server_default='completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='CASCADE')
    )

    # Tạo bảng scene_images
    op.create_table('scene_images',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('scene_id', sa.String(36), nullable=False),
        sa.Column('image_url', sa.String(), nullable=False),
        sa.Column('prompt', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='CASCADE')
    )

def downgrade():
    # Xóa các bảng theo thứ tự ngược lại
    op.drop_table('scene_images')
    op.drop_table('voice_audios')
    op.drop_table('scenes')
    op.drop_table('video_scripts')
    op.drop_table('refresh_tokens')
    op.drop_table('users') 