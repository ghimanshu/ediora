"""Assign unique editor codes and stable journal URL slugs."""
import re
import secrets
import string
import unicodedata
from alembic import op
import sqlalchemy as sa
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("editors", sa.Column("public_code", sa.String(8), nullable=True))
    op.add_column("editor_journals", sa.Column("slug", sa.String(150), nullable=True))
    connection = op.get_bind()
    editors = sa.table("editors", sa.column("id", sa.Integer()), sa.column("public_code", sa.String(8)))
    used = set()
    for editor_id in connection.execute(sa.select(editors.c.id)).scalars().all():
        while True:
            code = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
            if code not in used:
                break
        used.add(code)
        connection.execute(editors.update().where(editors.c.id == editor_id).values(public_code=code))
    journals = sa.table("editor_journals", sa.column("id", sa.Integer()), sa.column("name", sa.String(150)), sa.column("slug", sa.String(150)))
    for row in connection.execute(sa.select(journals.c.id, journals.c.name)).all():
        normalized = unicodedata.normalize("NFKD", row.name).encode("ascii", "ignore").decode().lower()
        slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:150].rstrip("-") or "journal"
        connection.execute(journals.update().where(journals.c.id == row.id).values(slug=slug))
    with op.batch_alter_table("editors") as batch:
        batch.alter_column("public_code", existing_type=sa.String(8), nullable=False)
        batch.create_unique_constraint("uq_editors_public_code", ["public_code"])
    with op.batch_alter_table("editor_journals") as batch:
        batch.alter_column("slug", existing_type=sa.String(150), nullable=False)

def downgrade():
    with op.batch_alter_table("editor_journals") as batch:
        batch.drop_column("slug")
    with op.batch_alter_table("editors") as batch:
        batch.drop_constraint("uq_editors_public_code", type_="unique")
        batch.drop_column("public_code")
