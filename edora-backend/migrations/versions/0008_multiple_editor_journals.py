"""Allow multiple journals per editor while preserving preview URL uniqueness."""
from alembic import op
import sqlalchemy as sa
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

def upgrade():
    constraints = sa.inspect(op.get_bind()).get_unique_constraints("editor_journals")
    existing = next(item for item in constraints if item["column_names"] == ["editor_id"])
    with op.batch_alter_table("editor_journals", naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"}) as batch:
        batch.drop_constraint(existing["name"] or "uq_editor_journals_editor_id", type_="unique")
        batch.create_unique_constraint("uq_editor_journal_slug", ["editor_id", "slug"])
        batch.create_index("ix_editor_journals_editor_id", ["editor_id"])

def downgrade():
    connection = op.get_bind()
    duplicate = connection.execute(sa.text("SELECT editor_id FROM editor_journals GROUP BY editor_id HAVING COUNT(*) > 1")).first()
    if duplicate:
        raise RuntimeError("Cannot downgrade while an editor owns multiple journals; no data was removed")
    with op.batch_alter_table("editor_journals") as batch:
        batch.drop_index("ix_editor_journals_editor_id")
        batch.drop_constraint("uq_editor_journal_slug", type_="unique")
        batch.create_unique_constraint("uq_editor_journals_editor_id", ["editor_id"])
