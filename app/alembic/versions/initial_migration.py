"""Initial migration

Revision ID: initial_migration
Revises: 
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial_migration'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('token', sa.String(255), unique=True, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )

    # Create video_scripts table
    op.create_table(
        'video_scripts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('creator_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('target_audience', sa.String(255)),
        sa.Column('total_duration', sa.Integer()),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )

    # Create scenes table
    op.create_table(
        'scenes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('script_id', sa.String(36), sa.ForeignKey('video_scripts.id')),
        sa.Column('scene_number', sa.Integer()),
        sa.Column('description', sa.Text()),
        sa.Column('duration', sa.Integer()),
        sa.Column('visual_elements', sa.Text()),  # Mô tả chi tiết cho việc tạo hình ảnh
        sa.Column('background_music', sa.String(255)),
        sa.Column('voice_over', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )

    # Create voice_audios table
    op.create_table(
        'voice_audios',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('script_id', sa.String(36), sa.ForeignKey('video_scripts.id')),
        sa.Column('scene_id', sa.String(36), sa.ForeignKey('scenes.id')),
        sa.Column('audio_url', sa.Text()),
        sa.Column('text_content', sa.Text()),
        sa.Column('voice_id', sa.String(20)),
        sa.Column('speed', sa.Float()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )

    # Create scene_images table
    op.create_table(
        'scene_images',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('scene_id', sa.String(36), sa.ForeignKey('scenes.id')),
        sa.Column('image_url', sa.Text()),
        sa.Column('prompt', sa.Text()),
        sa.Column('width', sa.Integer()),
        sa.Column('height', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )

def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('scene_images')
    op.drop_table('voice_audios')
    op.drop_table('scenes')
    op.drop_table('video_scripts')
    op.drop_table('refresh_tokens')
    op.drop_table('users')