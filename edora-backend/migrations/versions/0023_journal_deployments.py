"""Store immutable requested journal deployment versions."""
from alembic import op
import sqlalchemy as sa
revision="0023"
down_revision="0022"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("journal_deployments",sa.Column("id",sa.Integer,primary_key=True),sa.Column("journal_id",sa.Integer,sa.ForeignKey("editor_journals.id",ondelete="CASCADE"),nullable=False),sa.Column("version",sa.Integer,nullable=False),sa.Column("page_count",sa.Integer,nullable=False),sa.Column("snapshot",sa.JSON,nullable=False),sa.Column("website_zip",sa.LargeBinary,nullable=False),sa.Column("requested_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("journal_id","version",name="uq_journal_deployment_version"))
    op.create_index("ix_journal_deployments_journal_id","journal_deployments",["journal_id"])
def downgrade():
    op.drop_table("journal_deployments")
