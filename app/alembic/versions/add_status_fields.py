"""add status fields for script and media

Revision ID: add_status_fields
Revises: c1dcc092115b
Create Date: 2024-03-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_status_fields'
down_revision: Union[str, None] = 'c1dcc092115b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create enum types
    script_status = postgresql.ENUM('draft', 'processing', 'completed', 'failed', name='scriptstatus')
    media_status = postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='mediastatus')
    script_status.create(op.get_bind())
    media_status.create(op.get_bind())

    # Convert video_scripts.status to enum
    op.execute("ALTER TABLE video_scripts ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE video_scripts ALTER COLUMN status TYPE scriptstatus USING status::scriptstatus")
    op.execute("UPDATE video_scripts SET status = 'draft' WHERE status IS NULL")
    op.execute("ALTER TABLE video_scripts ALTER COLUMN status SET DEFAULT 'draft'::scriptstatus")
    op.alter_column('video_scripts', 'status', nullable=False)

    # Add status columns to scenes
    op.add_column('scenes', sa.Column('image_status', sa.Enum('pending', 'processing', 'completed', 'failed', name='mediastatus'), nullable=True))
    op.add_column('scenes', sa.Column('voice_status', sa.Enum('pending', 'processing', 'completed', 'failed', name='mediastatus'), nullable=True))
    op.execute("UPDATE scenes SET image_status = 'pending', voice_status = 'pending'")
    op.alter_column('scenes', 'image_status', nullable=False)
    op.alter_column('scenes', 'voice_status', nullable=False)

    # Add status column to voice_audios
    op.add_column('voice_audios', sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='mediastatus'), nullable=True))
    op.execute("UPDATE voice_audios SET status = 'completed'")
    op.alter_column('voice_audios', 'status', nullable=False)

    # Add status column to scene_images
    op.add_column('scene_images', sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='mediastatus'), nullable=True))
    op.execute("UPDATE scene_images SET status = 'completed'")
    op.alter_column('scene_images', 'status', nullable=False)

def downgrade() -> None:
    # Drop status columns
    op.drop_column('scene_images', 'status')
    op.drop_column('voice_audios', 'status')
    op.drop_column('scenes', 'voice_status')
    op.drop_column('scenes', 'image_status')
    
    # Revert video_scripts status to VARCHAR
    op.execute("ALTER TABLE video_scripts ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE video_scripts ALTER COLUMN status TYPE VARCHAR(20) USING status::VARCHAR")
    op.execute("UPDATE video_scripts SET status = 'draft' WHERE status IS NULL")
    op.execute("ALTER TABLE video_scripts ALTER COLUMN status SET DEFAULT 'draft'::VARCHAR")
    op.alter_column('video_scripts', 'status', nullable=False)

    # Drop enum types
    script_status = postgresql.ENUM(name='scriptstatus')
    media_status = postgresql.ENUM(name='mediastatus')
    script_status.drop(op.get_bind())
    media_status.drop(op.get_bind()) 