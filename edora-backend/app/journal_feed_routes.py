from datetime import datetime, timezone
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import Editor, EditorJournal, JournalIssue, JournalArticle

router = APIRouter(prefix="/api/v1/public/journals")

class ArticleOutput(BaseModel):
    id: int
    title: str
    authors: list[str]
    abstract: str
    article_url: str | None

class IssueOutput(BaseModel):
    id: int
    title: str
    volume: str
    number: str
    published_at: datetime
    articles: list[ArticleOutput]

class CurrentFeed(BaseModel):
    editor_code: str
    journal_slug: str
    issue: IssueOutput | None

class ArchivesFeed(BaseModel):
    editor_code: str
    journal_slug: str
    items: list[IssueOutput]
    total: int
    offset: int
    limit: int


def public_journal_id(db, editor_code, journal_slug):
    journal_id = db.scalar(select(EditorJournal.id).join(Editor, Editor.id == EditorJournal.editor_id).where(
        Editor.public_code == editor_code, Editor.role == "editor", Editor.is_active.is_(True), Editor.is_verified.is_(True),
        EditorJournal.slug == journal_slug, EditorJournal.status == "Published"))
    if journal_id is None:
        raise HTTPException(404, "Published journal not found")
    return journal_id

def issue_conditions(journal_id):
    return (JournalIssue.journal_id == journal_id, JournalIssue.is_published.is_(True),
            JournalIssue.published_at.is_not(None), JournalIssue.published_at <= datetime.now(timezone.utc))

def serialize_issues(db, issues):
    if not issues:
        return []
    articles = db.scalars(select(JournalArticle).where(JournalArticle.issue_id.in_([issue.id for issue in issues]),
                          JournalArticle.is_published.is_(True)).order_by(JournalArticle.position, JournalArticle.id)).all()
    grouped = {issue.id: [] for issue in issues}
    for article in articles:
        try:
            parsed = urlsplit(article.article_url)
            safe_url = article.article_url if parsed.scheme in {"http", "https"} and parsed.netloc and not parsed.username and not parsed.password else None
        except ValueError:
            safe_url = None
        grouped[article.issue_id].append({"id": article.id, "title": article.title, "authors": article.authors,
                                         "abstract": article.abstract, "article_url": safe_url})
    return [{"id": issue.id, "title": issue.title, "volume": issue.volume, "number": issue.number,
             "published_at": issue.published_at, "articles": grouped[issue.id]} for issue in issues]

@router.get("/{editor_code}/{journal_slug}/current", response_model=CurrentFeed)
def current(editor_code: str = Path(pattern=r"^[a-z0-9]{8}$"),
            journal_slug: str = Path(min_length=1, max_length=150, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"), db: DBSession = Depends(get_db)):
    journal_id = public_journal_id(db, editor_code, journal_slug)
    issue = db.scalar(select(JournalIssue).where(*issue_conditions(journal_id)).order_by(JournalIssue.published_at.desc(), JournalIssue.id.desc()).limit(1))
    return {"editor_code": editor_code, "journal_slug": journal_slug, "issue": serialize_issues(db, [issue])[0] if issue else None}

@router.get("/{editor_code}/{journal_slug}/archives", response_model=ArchivesFeed)
def archives(editor_code: str = Path(pattern=r"^[a-z0-9]{8}$"),
             journal_slug: str = Path(min_length=1, max_length=150, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
             offset: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), db: DBSession = Depends(get_db)):
    journal_id = public_journal_id(db, editor_code, journal_slug)
    filters = list(issue_conditions(journal_id))
    latest = db.scalar(select(JournalIssue.id).where(*filters).order_by(JournalIssue.published_at.desc(), JournalIssue.id.desc()).limit(1))
    if latest is not None:
        filters.append(JournalIssue.id != latest)
    total = db.scalar(select(func.count()).select_from(JournalIssue).where(*filters))
    issues = db.scalars(select(JournalIssue).where(*filters).order_by(JournalIssue.published_at.desc(), JournalIssue.id.desc()).offset(offset).limit(limit)).all()
    return {"editor_code": editor_code, "journal_slug": journal_slug, "items": serialize_issues(db, issues), "total": total, "offset": offset, "limit": limit}
