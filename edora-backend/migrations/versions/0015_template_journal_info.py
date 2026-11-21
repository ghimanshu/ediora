"""Enable journal information panels in starter admin templates."""
from alembic import op
import sqlalchemy as sa
revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

def upgrade():
    table = sa.table("website_templates", sa.column("id", sa.Integer), sa.column("name", sa.String), sa.column("layout", sa.JSON))
    db = op.get_bind()
    for row in db.execute(sa.select(table.c.id, table.c.layout).where(table.c.name.in_(["Classic Journal", "Sidebar Studio"]))):
        layout = dict(row.layout)
        layout["show_journal_info"] = True
        db.execute(table.update().where(table.c.id == row.id).values(layout=layout))

def downgrade():
    table = sa.table("website_templates", sa.column("id", sa.Integer), sa.column("name", sa.String), sa.column("layout", sa.JSON))
    db = op.get_bind()
    for row in db.execute(sa.select(table.c.id, table.c.layout).where(table.c.name.in_(["Classic Journal", "Sidebar Studio"]))):
        layout = dict(row.layout)
        layout.pop("show_journal_info", None)
        db.execute(table.update().where(table.c.id == row.id).values(layout=layout))
