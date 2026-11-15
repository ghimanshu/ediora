"""Add user roles and active status."""
from alembic import op
import sqlalchemy as sa
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("editors", sa.Column("role", sa.String(20), nullable=False, server_default="editor"))
    op.add_column("editors", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

def downgrade():
    op.drop_column("editors", "is_active")
    op.drop_column("editors", "role")
