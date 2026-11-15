"""Seed migration tests use only a new temporary SQLite database."""
import importlib.util
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, select
from app.page_schemas import PageInput


def test_journal_page_seed_preserves_content_and_is_repeatable(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'page-seed.db'}")
    metadata = MetaData()
    pages = Table("web_pages", metadata,
        Column("id", Integer, primary_key=True), Column("title", String(150)),
        Column("slug", String(150), unique=True), Column("content_html", Text),
        Column("created_at", DateTime(timezone=True)), Column("updated_at", DateTime(timezone=True)))
    metadata.create_all(engine)
    path = Path(__file__).resolve().parents[1] / "migrations/versions/0005_seed_journal_pages.py"
    spec = importlib.util.spec_from_file_location("journal_page_seed", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "0004"
    assert {page["slug"] for page in migration.PAGES} == {"home", "about-the-journal", "editorial-team", "submissions"}
    for page in migration.PAGES:
        validated = PageInput(**page)
        assert "https://www.eelet.org.uk/" in validated.content_html
        assert "<h1>" in validated.content_html
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            rows = connection.execute(select(pages)).mappings().all()
            assert len(rows) == 4
            for row in rows:
                assert row["created_at"] is not None and row["updated_at"] is not None
            editorial = next(row for row in rows if row["slug"] == "editorial-team")
            assert editorial["content_html"].count("Muhammad Umar Riaz Abbasi") == 1
            connection.execute(pages.update().where(pages.c.slug == "home").values(title="Custom homepage", content_html="<p>Keep my changes</p>"))
            connection.execute(pages.insert().values(title="Existing page", slug="custom", content_html="<p>Keep this too</p>"))
            # Repeat runs and rollback/re-upgrade must preserve authored content.
            migration.upgrade()
            migration.downgrade()
            migration.upgrade()
            rows = connection.execute(select(pages)).mappings().all()
            assert len(rows) == 5
            home = next(row for row in rows if row["slug"] == "home")
            assert home["title"] == "Custom homepage"
            assert home["content_html"] == "<p>Keep my changes</p>"
            assert any(row["slug"] == "custom" for row in rows)
    engine.dispose()
