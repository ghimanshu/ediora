import importlib.util
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa

def test_cleanup_updates_master_and_editor_content_without_losing_text():
    path = Path(__file__).resolve().parents[1] / "migrations/versions/0016_remove_eelet_links.py"
    spec = importlib.util.spec_from_file_location("eelet_cleanup", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    source = '<p><a href="https://www.eelet.org.uk/index.php/journal/about">About <strong>journal</strong></a> <a href="https://example.com">Keep</a></p>'
    expected = '<p>About <strong>journal</strong> <a href="https://example.com">Keep</a></p>'
    assert migration.clean_text(source) == expected
    assert migration.clean_text("https://eelet.org/path https://not-eelet.org/path") == " https://not-eelet.org/path"
    metadata = sa.MetaData()
    specs = [("website_templates", {"description": sa.String(), "layout": sa.JSON()}), ("web_pages", {"content_html": sa.Text()}), ("editor_journals", {"template_description": sa.String(), "template_layout": sa.JSON(), "journal_info": sa.JSON()}), ("editor_journal_pages", {"content_html": sa.Text()}), ("journal_articles", {"abstract": sa.Text(), "article_url": sa.String()})]
    tables = []
    for name, fields in specs:
        tables.append(sa.Table(name, metadata, sa.Column("id", sa.Integer(), primary_key=True), *(sa.Column(key, kind) for key, kind in fields.items())))
    engine = sa.create_engine("sqlite://")
    metadata.create_all(engine)
    with engine.begin() as db:
        for table in tables:
            db.execute(table.insert().values(id=1, **{col.name: {"text": source} if isinstance(col.type, sa.JSON) else source for col in table.columns if col.name != "id"}))
        with Operations.context(MigrationContext.configure(db)):
            migration.upgrade()
            migration.upgrade()
        for table in tables:
            row = db.execute(sa.select(table)).mappings().one()
            for col in table.columns:
                if col.name != "id":
                    assert row[col.name] == ({"text": expected} if isinstance(col.type, sa.JSON) else expected)
    engine.dispose()
