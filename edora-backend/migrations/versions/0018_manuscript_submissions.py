"""Store visitor manuscripts and single-use CAPTCHA challenges."""
from alembic import op
import sqlalchemy as sa
revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("submission_captchas", sa.Column("id",sa.String(64),primary_key=True),sa.Column("journal_id",sa.Integer,sa.ForeignKey("editor_journals.id",ondelete="CASCADE"),nullable=False),sa.Column("answer_hash",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_submission_captchas_journal_id","submission_captchas",["journal_id"])
    op.create_table("manuscript_submissions",sa.Column("id",sa.Integer,primary_key=True),sa.Column("journal_id",sa.Integer,sa.ForeignKey("editor_journals.id",ondelete="CASCADE"),nullable=False),sa.Column("full_name",sa.String(150),nullable=False),sa.Column("email",sa.String(254),nullable=False),sa.Column("title",sa.String(300),nullable=False),sa.Column("authors",sa.String(2000),nullable=False),sa.Column("abstract",sa.Text,nullable=False),sa.Column("pdf_content",sa.LargeBinary,nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("notification_sent",sa.Boolean,nullable=False,server_default=sa.false()))
    op.create_index("ix_manuscript_submissions_journal_id","manuscript_submissions",["journal_id"])

def downgrade():
    op.drop_table("manuscript_submissions")
    op.drop_table("submission_captchas")
