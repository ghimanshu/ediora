"""Store private journal template and page copies for each editor."""
from alembic import op
import sqlalchemy as sa
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("editor_journals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("editor_id", sa.Integer(), sa.ForeignKey("editors.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("template_name", sa.String(100), nullable=False),
        sa.Column("template_description", sa.String(500), nullable=False),
        sa.Column("template_layout", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("editor_journal_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("journal_id", sa.Integer(), sa.ForeignKey("editor_journals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("journal_id", "slug", name="uq_journal_page_slug"))
    op.create_index("ix_editor_journal_pages_journal_id", "editor_journal_pages", ["journal_id"])

def downgrade():
    op.drop_table("editor_journal_pages")
    op.drop_table("editor_journals")
