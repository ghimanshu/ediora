"""Store journal-specific editorial and publishing information."""
from alembic import op
import sqlalchemy as sa
revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("editor_journals", sa.Column("journal_info", sa.JSON(), nullable=False, server_default="{}"))

def downgrade():
    op.drop_column("editor_journals", "journal_info")
