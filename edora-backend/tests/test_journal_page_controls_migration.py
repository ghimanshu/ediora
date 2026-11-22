import importlib.util
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine,text

def test_page_origin_backfill_preserves_content_and_enables_existing_pages():
    path=Path(__file__).resolve().parents[1]/"migrations/versions/0021_journal_page_controls.py"
    spec=importlib.util.spec_from_file_location("page_controls",path)
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    engine=create_engine("sqlite://")
    with engine.begin() as db:
        db.execute(text("CREATE TABLE web_pages (id INTEGER PRIMARY KEY, slug TEXT)"))
        db.execute(text("CREATE TABLE editor_journal_pages (id INTEGER PRIMARY KEY, slug TEXT, content_html TEXT)"))
        db.execute(text("INSERT INTO web_pages VALUES (1,'about')"))
        db.execute(text("INSERT INTO editor_journal_pages VALUES (1,'about','Edited private copy'),(2,'my-page','Original editor content')"))
        with Operations.context(MigrationContext.configure(db)): migration.upgrade()
        rows=db.execute(text("SELECT source_type,is_active,content_html FROM editor_journal_pages ORDER BY id")).all()
        assert rows[0]==('admin',1,'Edited private copy')
        assert rows[1]==('editor',1,'Original editor content')
    engine.dispose()
