"""Create editors, verification tokens, sessions and contact requests."""
from alembic import op
import sqlalchemy as sa
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("editors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=False),
        sa.Column("phone", sa.String(25), nullable=False),
        sa.Column("gender", sa.String(30), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_editors_email", "editors", ["email"], unique=True)
    for table in ("verifications", "sessions"):
        op.create_table(table,
            sa.Column("token_hash", sa.String(64), primary_key=True),
            sa.Column("editor_id", sa.Integer(), sa.ForeignKey("editors.id", ondelete="CASCADE"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
        op.create_index(f"ix_{table}_editor_id", table, ["editor_id"])
    op.create_table("contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))

def downgrade():
    for table in ("contacts", "sessions", "verifications", "editors"):
        op.drop_table(table)
