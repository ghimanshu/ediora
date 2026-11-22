"""Track copied page origins and journal-only visibility."""
from alembic import op
import sqlalchemy as sa
revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("editor_journal_pages",sa.Column("source_type",sa.String(10),nullable=False,server_default="editor"))
    op.add_column("editor_journal_pages",sa.Column("is_active",sa.Boolean,nullable=False,server_default=sa.true()))
    # Older records did not preserve provenance. Existing admin slugs are treated conservatively as copies.
    op.execute("UPDATE editor_journal_pages SET source_type='admin' WHERE EXISTS (SELECT 1 FROM web_pages WHERE web_pages.slug=editor_journal_pages.slug)")

def downgrade():
    op.drop_column("editor_journal_pages","is_active")
    op.drop_column("editor_journal_pages","source_type")
