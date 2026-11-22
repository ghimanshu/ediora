from typing import Literal
import base64
import binascii
from datetime import datetime, date, time, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, field_validator, model_validator
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import Editor, EditorJournal, JournalArticle, JournalIssue, now
from app.journal_routes import editor_account, own_journal

router = APIRouter(prefix="/api/v1/editor")
MAX_PDF_BYTES = 10 * 1024 * 1024

class ArticleInput(BaseModel):
    how_to_cite: str = Field(default="", max_length=2000)
    volume_id: int | None = Field(default=None, gt=0, strict=True)
    status: Literal["Submitted", "Published", "UnPublished"] | None = None
    title: str = Field(min_length=1, max_length=300)
    authors: list[str] = Field(min_length=1, max_length=50)
    abstract: str = Field(default="", max_length=10000)
    is_published: bool = False
    pdf_base64: str | None = Field(default=None, max_length=13981020)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("authors")
    @classmethod
    def author_names(cls, names):
        if any(not name.strip() or len(name.strip()) > 120 for name in names):
            raise ValueError("Each author needs a name of 1 to 120 characters")
        return [name.strip() for name in names]

class ArticleOutput(BaseModel):
    how_to_cite: str
    status: Literal["Submitted", "Published", "UnPublished"]
    submitter_name: str
    submitter_email: str
    notification_sent: bool
    journal_name: str
    created_at: datetime
    id: int
    journal_id: int
    title: str
    authors: list[str]
    abstract: str
    is_published: bool
    volume_id: int | None
    volume_title: str | None
    has_pdf: bool
    pdf_size: int

class VolumeInput(BaseModel):
    status: Literal["Published", "UnPublished", "Archived"] | None = None
    is_archived: bool = False
    title: str = Field(min_length=1, max_length=200)
    volume: str = Field(min_length=1, max_length=40)
    number: str = Field(default="", max_length=40)
    is_published: bool = False
    published_at: AwareDatetime | None = None
    article_ids: list[int] = Field(default_factory=list, max_length=1000)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def exclusive_status(self):
        if self.status is not None:
            self.is_published = self.status != "UnPublished"
            self.is_archived = self.status == "Archived"
        elif not self.is_published:
            self.is_archived = False
        return self

    @field_validator("article_ids")
    @classmethod
    def distinct_articles(cls, values):
        if any(value <= 0 for value in values) or len(values) != len(set(values)):
            raise ValueError("Select each valid article only once")
        return values

class VolumeOutput(BaseModel):
    status: Literal["Published", "UnPublished", "Archived"]
    is_archived: bool
    journal_name: str
    created_at: datetime
    id: int
    journal_id: int
    title: str
    volume: str
    number: str
    is_published: bool
    published_at: datetime | None
    article_ids: list[int]


def article_output(db, article, journal_name=None):
    volume = db.get(JournalIssue, article.issue_id) if article.issue_id else None
    return {"status": article.status, "submitter_name": article.submitter_name, "submitter_email": article.submitter_email, "notification_sent": article.notification_sent, "journal_name": journal_name if journal_name is not None else db.get(EditorJournal, article.journal_id).name, "created_at": article.created_at, "id": article.id, "journal_id": article.journal_id, "title": article.title, "authors": article.authors,
            "how_to_cite": article.how_to_cite, "abstract": article.abstract, "is_published": article.is_published, "volume_id": article.issue_id,
            "volume_title": volume.title if volume else None, "has_pdf": article.pdf_size > 0, "pdf_size": article.pdf_size}

def volume_output(db, volume, journal_name=None):
    return {"journal_name": journal_name if journal_name is not None else db.get(EditorJournal, volume.journal_id).name, "created_at": volume.created_at, "id": volume.id, "journal_id": volume.journal_id, "title": volume.title, "volume": volume.volume,
            "number": volume.number, "status": "UnPublished" if not volume.is_published else "Archived" if volume.is_archived else "Published", "is_archived": volume.is_archived, "is_published": volume.is_published, "published_at": volume.published_at,
            "article_ids": db.scalars(select(JournalArticle.id).where(JournalArticle.journal_id == volume.journal_id,
                JournalArticle.issue_id == volume.id).order_by(JournalArticle.position, JournalArticle.id)).all()}

def find_article(db, journal_id, article_id):
    article = db.scalar(select(JournalArticle).where(JournalArticle.id == article_id, JournalArticle.journal_id == journal_id))
    if not article:
        raise HTTPException(404, "Article not found")
    return article

def find_volume(db, journal_id, volume_id):
    volume = db.scalar(select(JournalIssue).where(JournalIssue.id == volume_id, JournalIssue.journal_id == journal_id))
    if not volume:
        raise HTTPException(404, "Volume not found")
    return volume

def set_article_data(article, data, creating=False):
    if creating and not data.pdf_base64:
        raise HTTPException(422, "Upload a PDF for the new article")
    if data.pdf_base64 is not None:
        try:
            pdf = base64.b64decode(data.pdf_base64, validate=True)
        except (ValueError, binascii.Error):
            raise HTTPException(422, "Invalid PDF upload")
        if len(pdf) > MAX_PDF_BYTES:
            raise HTTPException(413, "PDF must not exceed 10 MB")
        if not pdf.startswith(b"%PDF-") or b"%%EOF" not in pdf[-2048:]:
            raise HTTPException(422, "Upload a valid PDF document")
        article.pdf_content = pdf
        article.pdf_filename = "article.pdf"
        article.pdf_size = len(pdf)
    status = data.status or ("Published" if data.is_published else "UnPublished")
    if status == "Published" and not article.pdf_size:
        raise HTTPException(422, "Add a PDF before publishing this article")
    excluded = {"pdf_base64", "status", "is_published", "volume_id"}
    if "how_to_cite" not in data.model_fields_set:
        excluded.add("how_to_cite")
    for key, value in data.model_dump(exclude=excluded).items():
        setattr(article, key, value)
    article.status = status
    article.is_published = status == "Published"

def assign_article_volume(db, journal, article, data):
    if "volume_id" not in data.model_fields_set:
        return
    target = find_volume(db, journal.id, data.volume_id) if data.volume_id is not None else None
    if article.issue_id == (target.id if target else None):
        return
    if target is None:
        article.issue_id = None
        article.position = 0
    else:
        last_position = db.scalar(select(func.max(JournalArticle.position)).where(JournalArticle.journal_id == journal.id, JournalArticle.issue_id == target.id))
        article.issue_id = target.id
        article.position = (last_position + 1) if last_position is not None else 0


def created_range(column, date_from, date_to):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "Created from must not be later than created to")
    filters = []
    if date_from:
        filters.append(column >= datetime.combine(date_from, time.min, timezone.utc))
    if date_to:
        if date_to == date.max:
            filters.append(column <= datetime.combine(date_to, time.max, timezone.utc))
        else:
            filters.append(column < datetime.combine(date_to + timedelta(days=1), time.min, timezone.utc))
    return filters

@router.get("/articles", response_model=list[ArticleOutput])
def articles(journal_id: int | None = Query(None, gt=0), date_from: date | None = None, date_to: date | None = None,
             editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    filters = [EditorJournal.editor_id == editor.id, *created_range(JournalArticle.created_at, date_from, date_to)]
    if journal_id is not None:
        own_journal(db, editor.id, journal_id)
        filters.append(JournalArticle.journal_id == journal_id)
    rows = db.execute(select(JournalArticle, EditorJournal.name).join(EditorJournal, EditorJournal.id == JournalArticle.journal_id).where(*filters).order_by(JournalArticle.created_at.desc(), JournalArticle.id.desc())).all()
    return [article_output(db, article, name) for article, name in rows]

@router.post("/articles", response_model=ArticleOutput, status_code=201)
def create_article(data: ArticleInput, journal_id: int = Query(gt=0), editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id, journal_id)
    article = JournalArticle(journal_id=journal.id, issue_id=None, pdf_size=0)
    set_article_data(article, data, creating=True)
    assign_article_volume(db, journal, article, data)
    db.add(article)
    journal.updated_at = now()
    db.commit()
    return article_output(db, article)

@router.patch("/articles/{article_id}", response_model=ArticleOutput)
def edit_article(article_id: int, data: ArticleInput, journal_id: int = Query(gt=0), editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id, journal_id)
    article = find_article(db, journal.id, article_id)
    set_article_data(article, data)
    assign_article_volume(db, journal, article, data)
    journal.updated_at = now()
    db.commit()
    return article_output(db, article)

@router.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int, journal_id: int = Query(gt=0), editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id, journal_id)
    db.delete(find_article(db, journal.id, article_id))
    journal.updated_at = now()
    db.commit()


def pdf_response(article, inline=False):
    if not article.pdf_size or not article.pdf_content:
        raise HTTPException(404, "PDF not found")
    disposition = "inline" if inline else "attachment"
    return Response(article.pdf_content, media_type="application/pdf", headers={"Content-Disposition": f'{disposition}; filename="article-{article.id}.pdf"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

@router.get("/articles/{article_id}/pdf")
def private_pdf(article_id: int, journal_id: int = Query(gt=0), inline: bool = False, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id, journal_id)
    return pdf_response(find_article(db, journal.id, article_id), inline=inline)

@router.get("/volumes", response_model=list[VolumeOutput])
def volumes(journal_id: int | None = Query(None, gt=0), date_from: date | None = None, date_to: date | None = None,
            editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    filters = [EditorJournal.editor_id == editor.id, *created_range(JournalIssue.created_at, date_from, date_to)]
    if journal_id is not None:
        own_journal(db, editor.id, journal_id)
        filters.append(JournalIssue.journal_id == journal_id)
    rows = db.execute(select(JournalIssue, EditorJournal.name).join(EditorJournal, EditorJournal.id == JournalIssue.journal_id).where(*filters).order_by(JournalIssue.created_at.desc(), JournalIssue.id.desc())).all()
    return [volume_output(db, volume, name) for volume, name in rows]


def save_volume(db, journal, data, volume=None):
    selected = db.scalars(select(JournalArticle).where(JournalArticle.journal_id == journal.id, JournalArticle.id.in_(data.article_ids))).all()
    if len(selected) != len(data.article_ids):
        raise HTTPException(404, "One or more articles do not belong to this journal")
    if any(article.issue_id is not None and (volume is None or article.issue_id != volume.id) for article in selected):
        raise HTTPException(409, "An article already belongs to another volume. Remove it there before moving it.")
    if volume is None:
        volume = JournalIssue(journal_id=journal.id)
        db.add(volume)
    volume.title, volume.volume, volume.number = data.title, data.volume, data.number
    volume.is_archived = data.is_archived
    volume.is_published = data.is_published
    volume.published_at = (data.published_at or volume.published_at or now()) if data.is_published else data.published_at
    db.flush()
    current = db.scalars(select(JournalArticle).where(JournalArticle.journal_id == journal.id, JournalArticle.issue_id == volume.id)).all()
    for article in current:
        if article.id not in data.article_ids:
            article.issue_id = None
    by_id = {article.id: article for article in selected}
    for position, article_id in enumerate(data.article_ids):
        by_id[article_id].issue_id = volume.id
        by_id[article_id].position = position
    journal.updated_at = now()
    db.commit()
    return volume_output(db, volume)

@router.post("/volumes", response_model=VolumeOutput, status_code=201)
def create_volume(data: VolumeInput, journal_id: int = Query(gt=0), editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    return save_volume(db, own_journal(db, editor.id, journal_id), data)

@router.patch("/volumes/{volume_id}", response_model=VolumeOutput)
def edit_volume(volume_id: int, data: VolumeInput, journal_id: int = Query(gt=0), editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id, journal_id)
    return save_volume(db, journal, data, find_volume(db, journal.id, volume_id))

@router.delete("/volumes/{volume_id}", status_code=204)
def delete_volume(volume_id: int, journal_id: int = Query(gt=0), editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id, journal_id)
    volume = find_volume(db, journal.id, volume_id)
    for article in db.scalars(select(JournalArticle).where(JournalArticle.journal_id == journal.id, JournalArticle.issue_id == volume.id)).all():
        article.issue_id = None
    db.flush()
    db.delete(volume)
    journal.updated_at = now()
    db.commit()
