"""Store issue and article data for public Current/Archives feeds."""
from alembic import op
import sqlalchemy as sa
revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("journal_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("journal_id", sa.Integer(), sa.ForeignKey("editor_journals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("volume", sa.String(40), nullable=False),
        sa.Column("number", sa.String(40), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_journal_issues_journal_id", "journal_issues", ["journal_id"])
    op.create_table("journal_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("journal_issues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("article_url", sa.String(2048), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_journal_articles_issue_id", "journal_articles", ["issue_id"])

def downgrade():
    op.drop_table("journal_articles")
    op.drop_table("journal_issues")
