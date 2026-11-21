"""Unify visitor manuscripts with journal articles and preserve existing submissions."""
import re
from alembic import op
import sqlalchemy as sa
revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

def upgrade():
    for column in [sa.Column("status",sa.String(20),nullable=False,server_default="UnPublished"),sa.Column("submitter_name",sa.String(150),nullable=False,server_default=""),sa.Column("submitter_email",sa.String(254),nullable=False,server_default=""),sa.Column("notification_sent",sa.Boolean,nullable=False,server_default=sa.false()),sa.Column("source_submission_id",sa.Integer,nullable=True)]:
        op.add_column("journal_articles",column)
    op.create_index("uq_article_source_submission","journal_articles",["source_submission_id"],unique=True)
    db=op.get_bind()
    db.execute(sa.text("UPDATE journal_articles SET status=CASE WHEN is_published THEN 'Published' ELSE 'UnPublished' END"))
    metadata=sa.MetaData()
    articles=sa.Table("journal_articles",metadata,autoload_with=db)
    submissions=sa.Table("manuscript_submissions",metadata,autoload_with=db)
    for row in db.execute(sa.select(submissions)).mappings():
        authors=[name.strip() for name in re.split(r"[,;\n]+",row["authors"]) if name.strip()] or [row["full_name"]]
        db.execute(articles.insert().values(journal_id=row["journal_id"],issue_id=None,title=row["title"],authors=authors,abstract=row["abstract"],article_url="",position=0,is_published=False,status="Submitted",pdf_content=row["pdf_content"],pdf_filename="manuscript.pdf",pdf_size=len(row["pdf_content"]),created_at=row["created_at"],updated_at=row["created_at"],submitter_name=row["full_name"],submitter_email=row["email"],notification_sent=row["notification_sent"],source_submission_id=row["id"]))
    # Keep the legacy rows as an untouched migration backup; all new writes use articles.

def downgrade():
    op.drop_index("uq_article_source_submission",table_name="journal_articles")
    for column in ("source_submission_id","notification_sent","submitter_email","submitter_name","status"):
        op.drop_column("journal_articles",column)
