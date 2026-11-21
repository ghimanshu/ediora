"""Persist custom and built-in journal menu order."""
from alembic import op
import sqlalchemy as sa
revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("editor_journals", sa.Column("menu_order", sa.JSON(), nullable=False, server_default="[]"))

def downgrade():
    op.drop_column("editor_journals", "menu_order")
