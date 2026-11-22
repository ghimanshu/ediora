"""Add optional citation text to journal articles."""
from alembic import op
import sqlalchemy as sa
revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("journal_articles",sa.Column("how_to_cite",sa.Text(),nullable=False,server_default=""))

def downgrade():
    op.drop_column("journal_articles","how_to_cite")
