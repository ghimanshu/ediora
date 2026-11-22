import importlib.util
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

def test_policy_library_groups_and_existing_content():
    path=Path(__file__).resolve().parents[1]/"migrations/versions/0022_policy_page_menus.py"
    spec=importlib.util.spec_from_file_location("policy_pages",path)
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    engine=create_engine("sqlite://")
    with engine.begin() as db:
        db.execute(text("CREATE TABLE web_pages (id INTEGER PRIMARY KEY, title TEXT, slug TEXT UNIQUE, content_html TEXT, created_at DATETIME, updated_at DATETIME)"))
        db.execute(text("CREATE TABLE editor_journal_pages (id INTEGER PRIMARY KEY, content_html TEXT)"))
        db.execute(text("INSERT INTO web_pages (title,slug,content_html) VALUES ('Custom guidelines','author-guidelines','Keep my content')"))
        db.execute(text("INSERT INTO editor_journal_pages VALUES (1,'Private editor copy')"))
        with Operations.context(MigrationContext.configure(db)): migration.upgrade()
        rows=db.execute(text("SELECT slug,menu_group,content_html FROM web_pages")).all()
        assert len(rows)==8
        assert sum(r.menu_group=='Ethics' for r in rows)==4
        assert sum(r.menu_group=='For Authors' for r in rows)==3
        assert next(r for r in rows if r.slug=='author-guidelines').content_html=='Keep my content'
        assert all('eelet.org' not in r.content_html for r in rows)
        assert db.execute(text("SELECT content_html,menu_group FROM editor_journal_pages")).one()==('Private editor copy','')
    engine.dispose()
