"""Record volume creation dates for editor list filtering."""
from alembic import op
import sqlalchemy as sa
revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

def upgrade():
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("journal_issues", recreate=recreate) as batch:
        batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

def downgrade():
    op.drop_column("journal_issues", "created_at")
