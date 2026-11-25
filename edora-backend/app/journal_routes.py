from app.journal_menu import menu_order, system_pages
from copy import deepcopy
import re
import unicodedata
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import Editor, Session, Verification, WebPage, WebsiteTemplate, EditorJournal, EditorJournalPage, JournalDeployment, JournalArticle, JournalIssue, ManuscriptSubmission, SubmissionCaptcha, now
from app.routes import current_editor, verification_email
from app.schemas import EditorProfileInput, EditorOutput
from app.page_schemas import PageInput, PageOutput, PageSummary
from app.template_schemas import TemplateInput, TemplateLayout
from app.journal_schemas import JournalInfo, JournalCreate, JournalOutput, JournalPageOrder, JournalSummary, JournalStatusUpdate, JournalPageStatus

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

def own_journal(db, editor_id, journal_id=None):
    statement = select(EditorJournal).where(EditorJournal.editor_id == editor_id)
    if journal_id is not None:
        statement = statement.where(EditorJournal.id == journal_id)
    journals = db.scalars(statement.order_by(EditorJournal.id).limit(2).with_for_update()).all()
    if not journals:
        raise HTTPException(404, "Journal not found")
    if len(journals) > 1:
        raise HTTPException(409, "Select a journal before managing its content")
    return journals[0]

@router.get("/journals", response_model=list[JournalSummary])
def list_journals(editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    count = select(func.count(EditorJournalPage.id)).where(EditorJournalPage.journal_id == EditorJournal.id).correlate(EditorJournal).scalar_subquery()
    rows = db.execute(select(EditorJournal, count.label("page_count")).where(EditorJournal.editor_id == editor.id).order_by(EditorJournal.created_at.desc(), EditorJournal.id.desc())).all()
    return [{"id": journal.id, "name": journal.name, "slug": journal.slug, "status": journal.status, "template_name": journal.template_name,
             "page_count": page_count, "created_at": journal.created_at, "updated_at": journal.updated_at} for journal, page_count in rows]

def journal_output(db, journal):
    owner = db.get(Editor, journal.editor_id)
    pages = db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id == journal.id).order_by(EditorJournalPage.position)).all()
    active_pages = [page for page in pages if page.is_active]
    inactive_slugs = [page.slug for page in pages if not page.is_active]
    defaults = system_pages(active_pages,inactive_slugs)
    first_page = next((page.slug for page in active_pages if page.slug == "home"), active_pages[0].slug if active_pages else defaults[0][0] if defaults else "current")
    return {"menu_order": menu_order(journal, pages), "journal_info": journal.journal_info or {}, "id": journal.id, "name": journal.name, "status": journal.status, "editor_code": owner.public_code,
            "slug": journal.slug, "preview_path": f"/{owner.public_code}/{journal.slug}/{first_page}",
            "template_name": journal.template_name,
            "template_description": journal.template_description, "template_layout": journal.template_layout,
            "pages": pages, "created_at": journal.created_at, "updated_at": journal.updated_at}

@router.get("/journal", response_model=JournalOutput | None)
def get_journal(editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db), journal_id: int | None = Query(None, gt=0)):
    if journal_id is not None:
        return journal_output(db, own_journal(db, editor.id, journal_id))
    journals = db.scalars(select(EditorJournal).where(EditorJournal.editor_id == editor.id).order_by(EditorJournal.id).limit(2)).all()
    if len(journals) > 1:
        raise HTTPException(409, "Select a journal before managing its content")
    return journal_output(db, journals[0]) if journals else None

@router.post("/journal", response_model=JournalOutput, status_code=201)
def create_journal(data: JournalCreate, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    db.scalar(select(Editor).where(Editor.id == editor.id).with_for_update())
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
    if db.scalar(select(EditorJournal.id).where(EditorJournal.editor_id == editor.id, EditorJournal.slug == slug)):
        raise HTTPException(409, "You already have a journal with this website slug. Choose a different name.")
    journal = EditorJournal(editor_id=editor.id, name=data.name, slug=slug, template_name=template.name,
                            template_description=template.description, template_layout=layout)
    try:
        db.add(journal)
        db.flush()
        source_map = {page.id: page for page in sources}
        for position, page_id in enumerate(data.page_ids):
            page = source_map[page_id]
            safe = PageInput(title=page.title, slug=page.slug, content_html=page.content_html)
            db.add(EditorJournalPage(journal_id=journal.id, position=position, source_type="admin", menu_group=page.menu_group, **safe.model_dump()))
        for offset, page in enumerate(data.new_pages):
            db.add(EditorJournalPage(journal_id=journal.id, position=len(data.page_ids) + offset, **page.model_dump()))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Journal creation conflicted with another request; refresh and try again")
    return journal_output(db, journal)

@router.patch("/journal/template", response_model=JournalOutput)
def update_journal_template(data: TemplateInput, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db), journal_id: int | None = Query(None, gt=0)):
    journal = own_journal(db, editor.id, journal_id)
    journal.template_name = data.name
    journal.template_description = data.description
    journal.template_layout = data.layout.model_dump()
    journal.updated_at = now()
    db.commit()
    return journal_output(db, journal)

@router.post("/journal/pages", response_model=JournalOutput, status_code=201)
def add_journal_page(data: PageInput, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db), journal_id: int | None = Query(None, gt=0)):
    journal = own_journal(db, editor.id, journal_id)
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
def reorder_journal_pages(data: JournalPageOrder, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db), journal_id: int | None = Query(None, gt=0)):
    journal = own_journal(db, editor.id, journal_id)
    pages = db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id == journal.id)).all()
    by_id = {page.id: page for page in pages}
    system_slugs = {slug for slug, _ in system_pages(pages)}
    expected = set(by_id) | system_slugs if any(isinstance(item, str) for item in data.page_ids) else set(by_id)
    if set(data.page_ids) != expected:
        raise HTTPException(409, "Include all journal pages and built-in pages exactly once. Refresh if the page list changed.")
    journal.menu_order = [by_id[item].slug if isinstance(item, int) else item for item in data.page_ids]
    for position, page_id in enumerate(data.page_ids):
        if isinstance(page_id, int):
            by_id[page_id].position = position
    journal.updated_at = now()
    db.commit()
    return journal_output(db, journal)

@router.patch("/journal/pages/{page_id}", response_model=JournalOutput)
def update_journal_page(page_id: int, data: PageInput, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db), journal_id: int | None = Query(None, gt=0)):
    journal = own_journal(db, editor.id, journal_id)
    page = db.scalar(select(EditorJournalPage).where(EditorJournalPage.id == page_id, EditorJournalPage.journal_id == journal.id))
    if not page:
        raise HTTPException(404, "Journal page not found")
    journal.menu_order = [data.slug if slug == page.slug else slug for slug in (journal.menu_order or [])]
    for key, value in data.model_dump().items():
        setattr(page, key, value)
    journal.updated_at = now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Your journal already contains a page with this slug")
    return journal_output(db, journal)


@router.patch("/journal/status", response_model=JournalOutput)
def update_journal_status(data: JournalStatusUpdate, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db), journal_id: int | None = Query(None, gt=0)):
    journal = own_journal(db, editor.id, journal_id)
    journal.status = data.status
    journal.updated_at = now()
    db.commit()
    return journal_output(db, journal)

@router.patch("/journal/info", response_model=JournalOutput)
def update_journal_info(data: JournalInfo, editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db), journal_id: int = Query(gt=0)):
    journal = own_journal(db, editor.id, journal_id)
    journal.journal_info = data.model_dump()
    journal.updated_at = now()
    db.commit()
    return journal_output(db, journal)

@router.delete("/journal", status_code=204)
def delete_journal(journal_id: int = Query(gt=0), editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id, journal_id)
    db.execute(delete(JournalDeployment).where(JournalDeployment.journal_id == journal.id))
    db.execute(delete(SubmissionCaptcha).where(SubmissionCaptcha.journal_id == journal.id))
    db.execute(delete(ManuscriptSubmission).where(ManuscriptSubmission.journal_id == journal.id))
    db.execute(delete(JournalArticle).where(JournalArticle.journal_id == journal.id))
    db.execute(delete(JournalIssue).where(JournalIssue.journal_id == journal.id))
    db.execute(delete(EditorJournalPage).where(EditorJournalPage.journal_id == journal.id))
    db.delete(journal)
    db.commit()

@router.delete("/journal/pages/{page_id}",response_model=JournalOutput)
def delete_own_page(page_id: int,journal_id: int=Query(gt=0),editor: Editor=Depends(editor_account),db: DBSession=Depends(get_db)):
    journal=own_journal(db,editor.id,journal_id)
    page=db.scalar(select(EditorJournalPage).where(EditorJournalPage.id==page_id,EditorJournalPage.journal_id==journal.id))
    if not page:
        raise HTTPException(404,"Journal page not found")
    if page.source_type!="editor":
        raise HTTPException(403,"Admin page copies can be deactivated, not deleted")
    journal.menu_order=[slug for slug in (journal.menu_order or []) if slug!=page.slug]
    db.delete(page)
    journal.updated_at=now()
    db.commit()
    return journal_output(db,journal)

@router.patch("/journal/pages/{page_id}/status",response_model=JournalOutput)
def set_admin_page_status(page_id: int,data: JournalPageStatus,journal_id: int=Query(gt=0),editor: Editor=Depends(editor_account),db: DBSession=Depends(get_db)):
    journal=own_journal(db,editor.id,journal_id)
    page=db.scalar(select(EditorJournalPage).where(EditorJournalPage.id==page_id,EditorJournalPage.journal_id==journal.id))
    if not page:
        raise HTTPException(404,"Journal page not found")
    if page.source_type!="admin":
        raise HTTPException(403,"Only admin page copies use this visibility control")
    page.is_active=data.is_active
    journal.updated_at=now()
    db.commit()
    return journal_output(db,journal)


@router.post("/journal/pages/library/{page_id}", response_model=JournalOutput)
def activate_library_page(page_id: int, journal_id: int = Query(gt=0), editor: Editor = Depends(editor_account), db: DBSession = Depends(get_db)):
    journal = own_journal(db, editor.id, journal_id)
    source = db.get(WebPage, page_id)
    if not source:
        raise HTTPException(404, "Admin page no longer available; refresh the page list")
    pages = db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id == journal.id)).all()
    existing = next((page for page in pages if page.slug == source.slug), None)
    if existing:
        if existing.source_type != "admin":
            raise HTTPException(409, "A personal page already uses this URL slug")
        existing.is_active = True
    else:
        if len(pages) >= 100:
            raise HTTPException(409, "A journal can contain at most 100 pages")
        safe = PageInput(title=source.title, slug=source.slug, content_html=source.content_html)
        db.add(EditorJournalPage(journal_id=journal.id, position=max((page.position for page in pages), default=-1)+1,
                                source_type="admin", menu_group=source.menu_group, is_active=True, **safe.model_dump()))
    journal.updated_at = now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Page list changed; refresh and try again")
    return journal_output(db, journal)
