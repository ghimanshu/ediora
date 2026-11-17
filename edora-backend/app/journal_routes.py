from copy import deepcopy
import re
import unicodedata
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import Editor, Session, Verification, WebPage, WebsiteTemplate, EditorJournal, EditorJournalPage, now
from app.routes import current_editor, verification_email
from app.schemas import EditorProfileInput, EditorOutput
from app.page_schemas import PageInput, PageOutput, PageSummary
from app.template_schemas import TemplateInput, TemplateLayout
from app.journal_schemas import JournalCreate, JournalOutput, JournalPageOrder

router = APIRouter(prefix="/api/v1/editor")

def editor_account(editor: Editor = Depends(current_editor)):
    if editor.role != "editor":
        raise HTTPException(403, "Editor account required")
    return editor

@router.patch("/profile", response_model=EditorOutput)
def update_profile(data: EditorProfileInput, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    editor = db.scalar(select(Editor).where(Editor.id == editor.id).with_for_update())
    email_changed = editor.email != data.email
    try:
        for key, value in data.model_dump().items():
            setattr(editor, key, value)
        if email_changed:
            editor.is_verified = False
            with db.no_autoflush:
                db.execute(delete(Session).where(Session.editor_id == editor.id))
                db.execute(delete(Verification).where(Verification.editor_id == editor.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email is already registered")
    if email_changed:
        verification_email(db, editor)
    return editor

@router.get("/pages", response_model=list[PageSummary])
def page_library(editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    return db.scalars(select(WebPage).order_by(WebPage.id)).all()

@router.get("/pages/{page_id}", response_model=PageOutput)
def library_page(page_id: int, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    page = db.get(WebPage, page_id)
    if not page:
        raise HTTPException(404, "Page not found")
    return page

def own_journal(db, editor_id):
    journal = db.scalar(select(EditorJournal).where(EditorJournal.editor_id == editor_id).with_for_update())
    if not journal:
        raise HTTPException(404, "Create your journal first")
    return journal

def journal_output(db, journal):
    owner = db.get(Editor, journal.editor_id)
    pages = db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id == journal.id).order_by(EditorJournalPage.position)).all()
    first_page = next((page.slug for page in pages if page.slug == "home"), pages[0].slug if pages else "current")
    return {"id": journal.id, "name": journal.name, "editor_code": owner.public_code,
            "slug": journal.slug, "preview_path": f"/{owner.public_code}/{journal.slug}/{first_page}",
            "template_name": journal.template_name,
            "template_description": journal.template_description, "template_layout": journal.template_layout,
            "pages": pages, "created_at": journal.created_at, "updated_at": journal.updated_at}

@router.get("/journal", response_model=JournalOutput | None)
def get_journal(editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = db.scalar(select(EditorJournal).where(EditorJournal.editor_id == editor.id))
    return journal_output(db, journal) if journal else None

@router.post("/journal", response_model=JournalOutput, status_code=201)
def create_journal(data: JournalCreate, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    db.scalar(select(Editor).where(Editor.id == editor.id).with_for_update())
    if db.scalar(select(EditorJournal.id).where(EditorJournal.editor_id == editor.id)):
        raise HTTPException(409, "You already have a journal")
    template = db.scalar(select(WebsiteTemplate).where(WebsiteTemplate.id == data.template_id).with_for_update())
    if not template:
        raise HTTPException(404, "Template not found; refresh the template library")
    sources = db.scalars(select(WebPage).where(WebPage.id.in_(data.page_ids)).order_by(WebPage.id).with_for_update()).all()
    if len(sources) != len(data.page_ids):
        raise HTTPException(404, "A selected page is no longer available; refresh the page library")
    all_slugs = [page.slug for page in sources] + [page.slug for page in data.new_pages]
    if len(set(all_slugs)) != len(all_slugs):
        raise HTTPException(409, "Each selected or new page must have a different URL slug")
    # These are independent values, never live references to administrator records.
    layout = TemplateLayout.model_validate(deepcopy(template.layout)).model_dump()
    normalized_name = unicodedata.normalize("NFKD", data.name).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_name).strip("-")[:150].rstrip("-") or "journal"
    journal = EditorJournal(editor_id=editor.id, name=data.name, slug=slug, template_name=template.name,
                            template_description=template.description, template_layout=layout)
    try:
        db.add(journal)
        db.flush()
        source_map = {page.id: page for page in sources}
        for position, page_id in enumerate(data.page_ids):
            page = source_map[page_id]
            safe = PageInput(title=page.title, slug=page.slug, content_html=page.content_html)
            db.add(EditorJournalPage(journal_id=journal.id, position=position, **safe.model_dump()))
        for offset, page in enumerate(data.new_pages):
            db.add(EditorJournalPage(journal_id=journal.id, position=len(data.page_ids) + offset, **page.model_dump()))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Journal creation conflicted with another request; refresh and try again")
    return journal_output(db, journal)

@router.patch("/journal/template", response_model=JournalOutput)
def update_journal_template(data: TemplateInput, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id)
    journal.template_name = data.name
    journal.template_description = data.description
    journal.template_layout = data.layout.model_dump()
    journal.updated_at = now()
    db.commit()
    return journal_output(db, journal)

@router.post("/journal/pages", response_model=JournalOutput, status_code=201)
def add_journal_page(data: PageInput, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id)
    pages = db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id == journal.id)).all()
    if len(pages) >= 100:
        raise HTTPException(409, "A journal can contain at most 100 pages")
    if any(page.slug == data.slug for page in pages):
        raise HTTPException(409, "Your journal already contains a page with this slug")
    position = max((page.position for page in pages), default=-1) + 1
    db.add(EditorJournalPage(journal_id=journal.id, position=position, **data.model_dump()))
    journal.updated_at = now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Your journal already contains a page with this slug")
    return journal_output(db, journal)

@router.patch("/journal/pages/order", response_model=JournalOutput)
def reorder_journal_pages(data: JournalPageOrder, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id)
    pages = db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id == journal.id)).all()
    if set(data.page_ids) != {page.id for page in pages}:
        raise HTTPException(409, "Include all of your journal pages exactly once. Refresh if the page list changed.")
    by_id = {page.id: page for page in pages}
    for position, page_id in enumerate(data.page_ids):
        by_id[page_id].position = position
    journal.updated_at = now()
    db.commit()
    return journal_output(db, journal)

@router.patch("/journal/pages/{page_id}", response_model=JournalOutput)
def update_journal_page(page_id: int, data: PageInput, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id)
    page = db.scalar(select(EditorJournalPage).where(EditorJournalPage.id == page_id, EditorJournalPage.journal_id == journal.id))
    if not page:
        raise HTTPException(404, "Journal page not found")
    for key, value in data.model_dump().items():
        setattr(page, key, value)
    journal.updated_at = now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Your journal already contains a page with this slug")
    return journal_output(db, journal)
