"""Add journal-owned articles, persistent PDFs and optional single-volume membership."""
from alembic import op
import sqlalchemy as sa
revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("journal_articles", sa.Column("journal_id", sa.Integer(), nullable=True))
    op.execute("UPDATE journal_articles SET journal_id = (SELECT journal_id FROM journal_issues WHERE journal_issues.id = journal_articles.issue_id)")
    with op.batch_alter_table("journal_issues") as batch:
        batch.create_unique_constraint("uq_issue_journal", ["id", "journal_id"])
    old = next(fk for fk in sa.inspect(op.get_bind()).get_foreign_keys("journal_articles") if fk["constrained_columns"] == ["issue_id"])
    convention = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
    with op.batch_alter_table("journal_articles", naming_convention=convention) as batch:
        batch.drop_constraint(old["name"] or "fk_journal_articles_issue_id_journal_issues", type_="foreignkey")
        batch.alter_column("journal_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("issue_id", existing_type=sa.Integer(), nullable=True)
        batch.create_foreign_key("fk_article_owner_journal", "editor_journals", ["journal_id"], ["id"], ondelete="CASCADE")
        batch.create_foreign_key("fk_article_volume_journal", "journal_issues", ["issue_id", "journal_id"], ["id", "journal_id"])
        batch.create_index("ix_journal_articles_journal_id", ["journal_id"])
        batch.add_column(sa.Column("pdf_content", sa.LargeBinary(), nullable=True))
        batch.add_column(sa.Column("pdf_filename", sa.String(255), nullable=True))
        batch.add_column(sa.Column("pdf_size", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        batch.create_check_constraint("ck_article_pdf_size", "pdf_size >= 0 AND pdf_size <= 10485760")

def downgrade():
    if op.get_bind().execute(sa.text("SELECT id FROM journal_articles WHERE issue_id IS NULL LIMIT 1")).first():
        raise RuntimeError("Assign unassigned articles before downgrade; no records were removed")
    with op.batch_alter_table("journal_articles") as batch:
        batch.drop_constraint("fk_article_volume_journal", type_="foreignkey")
        batch.drop_constraint("fk_article_owner_journal", type_="foreignkey")
        batch.drop_constraint("ck_article_pdf_size", type_="check")
        batch.drop_index("ix_journal_articles_journal_id")
        for name in ("pdf_content", "pdf_filename", "pdf_size", "created_at", "updated_at", "journal_id"):
            batch.drop_column(name)
        batch.alter_column("issue_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key("fk_journal_articles_issue_id_journal_issues", "journal_issues", ["issue_id"], ["id"], ondelete="CASCADE")
    with op.batch_alter_table("journal_issues") as batch:
        batch.drop_constraint("uq_issue_journal", type_="unique")
