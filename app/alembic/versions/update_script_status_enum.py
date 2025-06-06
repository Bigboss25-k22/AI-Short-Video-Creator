"""update script status enum

Revision ID: update_script_status_enum
Revises: add_status_fields
Create Date: 2024-06-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'update_script_status_enum'
down_revision: Union[str, None] = 'add_status_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tạo type enum mới
    op.execute("CREATE TYPE script_status AS ENUM ('draft', 'processing', 'completed', 'failed')")
    
    # Xóa giá trị mặc định hiện tại
    op.execute("ALTER TABLE video_scripts ALTER COLUMN status DROP DEFAULT")
    
    # Chuyển đổi dữ liệu từ enum cũ sang enum mới
    op.execute("""
        ALTER TABLE video_scripts 
        ALTER COLUMN status TYPE script_status 
        USING status::text::script_status
    """)
    
    # Thêm lại giá trị mặc định
    op.execute("ALTER TABLE video_scripts ALTER COLUMN status SET DEFAULT 'draft'::script_status")
    
    # Xóa type enum cũ nếu tồn tại
    op.execute("DROP TYPE IF EXISTS scriptstatus")


def downgrade() -> None:
    # Tạo lại type enum cũ
    op.execute("CREATE TYPE scriptstatus AS ENUM ('draft', 'processing', 'completed', 'failed')")
    
    # Xóa giá trị mặc định hiện tại
    op.execute("ALTER TABLE video_scripts ALTER COLUMN status DROP DEFAULT")
    
    # Chuyển đổi dữ liệu từ enum mới sang enum cũ
    op.execute("""
        ALTER TABLE video_scripts 
        ALTER COLUMN status TYPE scriptstatus 
        USING status::text::scriptstatus
    """)
    
    # Thêm lại giá trị mặc định
    op.execute("ALTER TABLE video_scripts ALTER COLUMN status SET DEFAULT 'draft'::scriptstatus")
    
    # Xóa type enum mới
    op.execute("DROP TYPE IF EXISTS script_status") 