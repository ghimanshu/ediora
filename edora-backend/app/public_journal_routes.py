from app.routes import bearer, current_editor
from fastapi.security import HTTPAuthorizationCredentials
from app.journal_menu import menu_order
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import Editor, EditorJournal, EditorJournalPage
from app.page_schemas import PageInput
from app.journal_schemas import PublicJournal

router = APIRouter(prefix="/api/v1/public/journals")

@router.get("/{editor_code}/{journal_slug}", response_model=PublicJournal)
def public_journal(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), editor_code: str = Path(pattern=r"^[a-z0-9]{8}$"),
                   journal_slug: str = Path(min_length=1, max_length=150, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
                   db: DBSession = Depends(get_db)):
    result = db.execute(select(EditorJournal, Editor.public_code, Editor.email).join(Editor, Editor.id == EditorJournal.editor_id).where(
        Editor.public_code == editor_code, EditorJournal.slug == journal_slug,
        Editor.role == "editor", Editor.is_active.is_(True), Editor.is_verified.is_(True))).first()
    if not result:
        raise HTTPException(404, "Journal not found")
    journal, code, email = result
    if journal.status != "Published":
        try:
            viewer=current_editor(request,credentials,db)
        except HTTPException:
            raise HTTPException(404,"Journal not found")
        if viewer.role != "super_admin" and viewer.id != journal.editor_id:
            raise HTTPException(404,"Journal not found")
    pages = db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id == journal.id).order_by(EditorJournalPage.position)).all()
    return {"menu_order": menu_order(journal, pages), "editor_email": email, "journal_info": journal.journal_info or {}, "name": journal.name, "slug": journal.slug, "editor_code": code, "template_layout": journal.template_layout,
            "pages": [PageInput(title=p.title, slug=p.slug, content_html=p.content_html).model_dump() for p in pages]}
