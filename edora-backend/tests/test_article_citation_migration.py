import importlib.util
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

def test_existing_articles_keep_content_and_get_empty_citation():
    path=Path(__file__).resolve().parents[1]/"migrations/versions/0020_article_citation.py"
    spec=importlib.util.spec_from_file_location("article_citation",path)
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    engine=create_engine("sqlite://")
    with engine.begin() as db:
        db.execute(text("CREATE TABLE journal_articles (id INTEGER PRIMARY KEY, title TEXT)"))
        db.execute(text("INSERT INTO journal_articles VALUES (1, 'Existing article')"))
        with Operations.context(MigrationContext.configure(db)): migration.upgrade()
        row=db.execute(text("SELECT title, how_to_cite FROM journal_articles WHERE id=1")).one()
        assert row.title=="Existing article" and row.how_to_cite==""
    engine.dispose()
