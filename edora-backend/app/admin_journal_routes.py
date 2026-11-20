from datetime import date, datetime, time, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import Editor, EditorJournal, EditorJournalPage
from app.routes import current_admin
from app.journal_routes import journal_output
from app.journal_schemas import JournalOutput, JournalStatus

router = APIRouter(prefix="/api/v1/admin")

class JournalEditorChoice(BaseModel):
    id: int
    name: str
    email: str

class AdminJournalSummary(BaseModel):
    preview_path: str
    id: int
    name: str
    template_name: str
    status: JournalStatus
    editor_id: int
    editor_name: str
    editor_email: str
    page_count: int
    created_at: datetime
    updated_at: datetime

class AdminJournalList(BaseModel):
    items: list[AdminJournalSummary]
    total: int

class AdminJournalDetail(JournalOutput):
    editor_id: int
    editor_name: str
    editor_email: str

@router.get("/journal-editors", response_model=list[JournalEditorChoice])
def journal_editors(admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    owners = select(EditorJournal.editor_id)
    editors = db.scalars(select(Editor).where(Editor.role == "editor", Editor.id.in_(owners)).order_by(Editor.first_name, Editor.last_name, Editor.id)).all()
    return [{"id": editor.id, "name": f"{editor.first_name} {editor.last_name}", "email": editor.email} for editor in editors]

@router.get("/editor-journals", response_model=AdminJournalList)
def editor_journals(editor_id: int | None = Query(None, gt=0), date_from: date | None = None, date_to: date | None = None,
                    offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
                    admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "Created from must not be later than created to")
    filters = [Editor.role == "editor"]
    if editor_id is not None:
        filters.append(EditorJournal.editor_id == editor_id)
    if date_from:
        filters.append(EditorJournal.created_at >= datetime.combine(date_from, time.min, timezone.utc))
    if date_to:
        # Exclusive next-day boundary includes every time on the selected end date.
        if date_to == date.max:
            filters.append(EditorJournal.created_at <= datetime.combine(date_to, time.max, timezone.utc))
        else:
            filters.append(EditorJournal.created_at < datetime.combine(date_to + timedelta(days=1), time.min, timezone.utc))
    page_count = select(func.count(EditorJournalPage.id)).where(EditorJournalPage.journal_id == EditorJournal.id).correlate(EditorJournal).scalar_subquery()
    first_slug = select(EditorJournalPage.slug).where(EditorJournalPage.journal_id == EditorJournal.id).order_by(
        case((EditorJournalPage.slug == "home", 0), else_=1), EditorJournalPage.position).limit(1).correlate(EditorJournal).scalar_subquery()
    statement = select(EditorJournal, Editor, page_count.label("page_count"), first_slug.label("first_slug")).join(Editor, Editor.id == EditorJournal.editor_id).where(*filters)
    rows = db.execute(statement.order_by(EditorJournal.created_at.desc(), EditorJournal.id.desc()).offset(offset).limit(limit)).all()
    total = db.scalar(select(func.count()).select_from(EditorJournal).join(Editor, Editor.id == EditorJournal.editor_id).where(*filters))
    return {"items": [{"id": journal.id, "name": journal.name, "template_name": journal.template_name, "status": journal.status,
                       "editor_id": editor.id, "editor_name": f"{editor.first_name} {editor.last_name}", "editor_email": editor.email,
                       "preview_path": f"/{editor.public_code}/{journal.slug}/{first_page or 'current'}",
                       "page_count": count, "created_at": journal.created_at, "updated_at": journal.updated_at} for journal, editor, count, first_page in rows], "total": total}

@router.get("/editor-journals/{journal_id}", response_model=AdminJournalDetail)
def view_editor_journal(journal_id: int, admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    result = db.execute(select(EditorJournal, Editor).join(Editor, Editor.id == EditorJournal.editor_id).where(EditorJournal.id == journal_id, Editor.role == "editor")).first()
    if not result:
        raise HTTPException(404, "Journal not found")
    journal, editor = result
    # Admin inspection deliberately works for inactive/unverified editor accounts too.
    return {**journal_output(db, journal), "editor_id": editor.id,
            "editor_name": f"{editor.first_name} {editor.last_name}", "editor_email": editor.email}
