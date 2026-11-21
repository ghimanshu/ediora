import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa

def test_existing_manuscript_becomes_submitted_article_without_losing_data():
    path=Path(__file__).resolve().parents[1]/"migrations/versions/0019_submitted_articles.py"
    spec=importlib.util.spec_from_file_location("submitted_articles",path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    metadata=sa.MetaData()
    articles=sa.Table("journal_articles",metadata,sa.Column("id",sa.Integer,primary_key=True),sa.Column("journal_id",sa.Integer),sa.Column("issue_id",sa.Integer),sa.Column("title",sa.String),sa.Column("authors",sa.JSON),sa.Column("abstract",sa.Text),sa.Column("article_url",sa.String),sa.Column("position",sa.Integer),sa.Column("is_published",sa.Boolean),sa.Column("pdf_content",sa.LargeBinary),sa.Column("pdf_filename",sa.String),sa.Column("pdf_size",sa.Integer),sa.Column("created_at",sa.DateTime(timezone=True)),sa.Column("updated_at",sa.DateTime(timezone=True)))
    legacy=sa.Table("manuscript_submissions",metadata,sa.Column("id",sa.Integer,primary_key=True),sa.Column("journal_id",sa.Integer),sa.Column("full_name",sa.String),sa.Column("email",sa.String),sa.Column("title",sa.String),sa.Column("authors",sa.String),sa.Column("abstract",sa.Text),sa.Column("pdf_content",sa.LargeBinary),sa.Column("created_at",sa.DateTime(timezone=True)),sa.Column("notification_sent",sa.Boolean))
    engine=sa.create_engine("sqlite://")
    metadata.create_all(engine)
    with engine.begin() as db:
        db.execute(articles.insert().values(id=7,title="Published article",is_published=True))
        db.execute(legacy.insert().values(id=3,journal_id=2,full_name="Visitor",email="visitor@example.com",title="Submitted manuscript",authors="Author One, Author Two",abstract="Original abstract",pdf_content=b"PDF bytes",created_at=datetime.now(timezone.utc),notification_sent=True))
        with Operations.context(MigrationContext.configure(db)): module.upgrade()
        updated=sa.Table("journal_articles",sa.MetaData(),autoload_with=db)
        rows=db.execute(sa.select(updated).order_by(updated.c.id)).mappings().all()
        assert rows[0]["status"]=="Published"
        submitted=rows[1]
        assert submitted["status"]=="Submitted" and not submitted["is_published"]
        assert submitted["journal_id"]==2 and submitted["issue_id"] is None
        assert submitted["authors"]==["Author One","Author Two"]
        assert submitted["pdf_content"]==b"PDF bytes" and submitted["pdf_size"]==9
        assert submitted["submitter_email"]=="visitor@example.com" and submitted["source_submission_id"]==3
    engine.dispose()
