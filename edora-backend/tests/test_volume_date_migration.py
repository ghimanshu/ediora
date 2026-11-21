import importlib.util
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

def test_existing_volume_survives_creation_date_backfill(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'volume-date.db'}")
    path = Path(__file__).resolve().parents[1] / "migrations/versions/0012_volume_creation_date.py"
    spec = importlib.util.spec_from_file_location("volume_date", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE journal_issues (id INTEGER PRIMARY KEY, title TEXT)"))
        connection.execute(text("INSERT INTO journal_issues VALUES (1, 'Existing volume')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        row = connection.execute(text("SELECT title, created_at FROM journal_issues WHERE id=1")).one()
        assert row.title == "Existing volume" and row.created_at is not None
    engine.dispose()
