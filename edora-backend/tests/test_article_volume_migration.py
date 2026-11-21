"""Verify existing feed articles survive migration and cross-journal assignment is constrained."""
import importlib.util
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

def test_article_volume_migration_preserves_records_and_membership(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'article-migration.db'}")
    path = Path(__file__).resolve().parents[1] / "migrations/versions/0011_article_volume_management.py"
    spec = importlib.util.spec_from_file_location("article_volume_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE editor_journals (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO editor_journals VALUES (1), (2)"))
        connection.execute(text("CREATE TABLE journal_issues (id INTEGER PRIMARY KEY, journal_id INTEGER NOT NULL REFERENCES editor_journals(id), title TEXT)"))
        connection.execute(text("INSERT INTO journal_issues VALUES (1, 1, 'Existing volume'), (2, 2, 'Other volume')"))
        connection.execute(text("CREATE TABLE journal_articles (id INTEGER PRIMARY KEY, issue_id INTEGER NOT NULL REFERENCES journal_issues(id) ON DELETE CASCADE, title TEXT)"))
        connection.execute(text("INSERT INTO journal_articles VALUES (1, 1, 'Existing research')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        row = connection.execute(text("SELECT journal_id, issue_id, title, pdf_size FROM journal_articles WHERE id=1")).one()
        assert tuple(row) == (1, 1, "Existing research", 0)
    with engine.connect() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        connection.commit()
        with pytest.raises(IntegrityError):
            connection.execute(text("UPDATE journal_articles SET issue_id=2 WHERE id=1"))
        connection.rollback()
        connection.execute(text("UPDATE journal_articles SET issue_id=NULL WHERE id=1"))
        connection.commit()
        assert connection.execute(text("SELECT title FROM journal_articles WHERE id=1")).scalar() == "Existing research"
    engine.dispose()
