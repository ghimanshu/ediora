"""Add persistent journal status, defaulting new and existing journals to Draft."""
from alembic import op
import sqlalchemy as sa
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("editor_journals") as batch:
        batch.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="Draft"))
        batch.create_check_constraint("ck_journal_status", "status IN ('Draft', 'Published', 'NotPublished')")

def downgrade():
    with op.batch_alter_table("editor_journals") as batch:
        batch.drop_constraint("ck_journal_status", type_="check")
        batch.drop_column("status")
