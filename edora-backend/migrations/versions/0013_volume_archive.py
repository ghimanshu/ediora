"""Allow editors to archive volumes explicitly."""
from alembic import op
import sqlalchemy as sa
revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("journal_issues", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column("journal_issues", "is_archived")
