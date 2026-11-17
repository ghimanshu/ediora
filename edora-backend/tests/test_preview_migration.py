"""URL migration backfill uses only a newly created temporary SQLite database."""
import importlib.util
from pathlib import Path
import re
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


def test_preview_url_migration_backfills_existing_records(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'preview-urls.db'}")
    path = Path(__file__).resolve().parents[1] / "migrations/versions/0007_journal_preview_urls.py"
    spec = importlib.util.spec_from_file_location("preview_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE editors (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO editors (id) VALUES (1), (2), (3)"))
        connection.execute(text("CREATE TABLE editor_journals (id INTEGER PRIMARY KEY, name VARCHAR(150))"))
        connection.execute(text("INSERT INTO editor_journals (id, name) VALUES (1, 'My Journal'), (2, '!!!')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            codes = connection.execute(text("SELECT public_code FROM editors")).scalars().all()
            assert len(set(codes)) == 3
            assert all(re.fullmatch(r"[a-z0-9]{8}", code) for code in codes)
            assert connection.execute(text("SELECT slug FROM editor_journals ORDER BY id")).scalars().all() == ["my-journal", "journal"]
            migration.downgrade()
            assert connection.execute(text("SELECT COUNT(*) FROM editors")).scalar() == 3
            assert connection.execute(text("SELECT name FROM editor_journals WHERE id=1")).scalar() == "My Journal"
    engine.dispose()
