from datetime import datetime, timedelta, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, delete, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from app.config import settings
from app.database import get_db
from app.models import Editor, Verification, Session, Contact, WebsiteTemplateSelection, EditorJournal, EditorJournalPage
from app.schemas import AdminUserUpdate, UserList, Register, Login, TokenInput, EditorOutput, EmailInput, ContactInput
from app.security import password_hasher, DUMMY_HASH, new_token, digest
from app.emails import send_email

router = APIRouter(prefix="/api/v1")
bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)
GENERIC = {"message": "If eligible, a verification email has been sent. Check your inbox."}

def now():
    return datetime.now(timezone.utc)

def verification_email(db, editor):
    # Caller locks the editor row so concurrent resends cannot create extra valid links.
    db.execute(delete(Verification).where(Verification.editor_id == editor.id))
    token = new_token()
    db.add(Verification(token_hash=digest(token), editor_id=editor.id,
                        expires_at=now() + timedelta(minutes=settings.verification_minutes)))
    db.commit()
    try:
        send_email(editor.email, "Verify your Edora email",
                   f"Welcome to Edora!\n\nVerify your email within {settings.verification_minutes} minutes:\n"
                   f"{settings.frontend_url}/verify-email?token={token}\n\nIf you did not register, ignore this email.")
    except Exception:
        # Keep account recoverable via resend; never log tokens or mail body.
        logger.warning("Verification delivery failed; use resend after checking SMTP configuration")

@router.post("/auth/register", status_code=202)
def register(data: Register, db: DBSession = Depends(get_db)):
    if db.scalar(select(Editor).where(Editor.email == data.email)):
        return GENERIC
    editor = Editor(**data.model_dump(exclude={"password"}), password_hash=password_hasher.hash(data.password))
    db.add(editor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return GENERIC
    editor = db.scalar(select(Editor).where(Editor.id == editor.id).with_for_update())
    verification_email(db, editor)
    return GENERIC

@router.post("/auth/resend-verification", status_code=202)
def resend(data: EmailInput, db: DBSession = Depends(get_db)):
    editor = db.scalar(select(Editor).where(Editor.email == data.email).with_for_update())
    if editor and not editor.is_verified:
        verification_email(db, editor)
    return GENERIC

@router.post("/auth/verify-email")
def verify(data: TokenInput, db: DBSession = Depends(get_db)):
    record = db.scalar(select(Verification).where(Verification.token_hash == digest(data.token),
                       Verification.expires_at > now()).with_for_update())
    if not record:
        raise HTTPException(400, "Verification link is invalid or expired. Request a new link.")
    editor = db.get(Editor, record.editor_id)
    editor.is_verified = True
    db.execute(delete(Verification).where(Verification.editor_id == editor.id))
    db.commit()
    return {"message": "Email verified. You can now sign in."}

@router.post("/auth/login")
def login(data: Login, db: DBSession = Depends(get_db)):
    editor = db.scalar(select(Editor).where(Editor.email == data.email))
    valid = password_hasher.verify(data.password, editor.password_hash if editor else DUMMY_HASH)
    if not editor or not valid:
        raise HTTPException(401, "Invalid email or password")
    if not editor.is_active:
        raise HTTPException(403, "Account is inactive")
    if not editor.is_verified:
        raise HTTPException(403, "Verify your email before signing in")
    token = new_token()
    db.add(Session(token_hash=digest(token), editor_id=editor.id,
                   expires_at=now() + timedelta(hours=settings.session_hours)))
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_in": settings.session_hours * 3600}

def current_editor(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: DBSession = Depends(get_db)):
    if not credentials:
        raise HTTPException(401, "Sign in required")
    session = db.scalar(select(Session).where(Session.token_hash == digest(credentials.credentials), Session.expires_at > now()))
    if not session:
        raise HTTPException(401, "Session expired or invalid")
    editor = db.get(Editor, session.editor_id)
    if not editor or not editor.is_verified or not editor.is_active:
        raise HTTPException(401, "Sign in required")
    return editor

@router.get("/auth/me", response_model=EditorOutput)
def me(editor: Editor = Depends(current_editor)):
    return editor

@router.post("/auth/logout", status_code=204)
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: DBSession = Depends(get_db)):
    if credentials:
        db.execute(delete(Session).where(Session.token_hash == digest(credentials.credentials)))
        db.commit()

@router.post("/contact", status_code=201)
def contact(data: ContactInput, db: DBSession = Depends(get_db)):
    record = Contact(**data.model_dump())
    db.add(record)
    db.commit()
    try:
        send_email(settings.contact_to, "New Edora contact request",
                   f"Name: {data.name}\nEmail: {data.email}\n\n{data.message}")
    except Exception:
        logger.warning("Contact notification failed; contact remains saved in database")
    return {"message": "Thank you. Your message has been saved."}

def current_admin(editor: Editor = Depends(current_editor)):
    if editor.role != "super_admin":
        raise HTTPException(403, "Super admin access required")
    return editor

@router.get("/admin/users", response_model=UserList)
def list_users(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
               search: str = Query("", max_length=254),
               admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    filters = []
    if search.strip():
        term = "%" + search.strip().replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
        filters.append(or_(*(column.ilike(term, escape="!") for column in
                            (Editor.email, Editor.first_name, Editor.last_name))))
    return {"items": db.scalars(select(Editor).where(*filters).order_by(Editor.id.desc()).offset(offset).limit(limit)).all(),
            "total": db.scalar(select(func.count()).select_from(Editor).where(*filters))}

def managed_user(db, user_id):
    editor = db.scalar(select(Editor).where(Editor.id == user_id).with_for_update())
    if not editor:
        raise HTTPException(404, "User not found")
    if editor.role == "super_admin":
        raise HTTPException(403, "Super admin accounts are protected")
    return editor

@router.patch("/admin/users/{user_id}", response_model=EditorOutput)
def update_user(user_id: int, data: AdminUserUpdate, admin: Editor = Depends(current_admin),
                db: DBSession = Depends(get_db)):
    editor = managed_user(db, user_id)
    email_changed = editor.email != data.email
    try:
        for key, value in data.model_dump(exclude={"password"}).items():
            setattr(editor, key, value)
        if email_changed:
            editor.is_verified = False
            db.execute(delete(Verification).where(Verification.editor_id == user_id))
        if email_changed or not editor.is_active:
            db.execute(delete(Session).where(Session.editor_id == user_id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email is already registered")
    return editor

@router.delete("/admin/users/{user_id}", status_code=204)
def delete_user(user_id: int, admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    editor = managed_user(db, user_id)
    journal_ids = select(EditorJournal.id).where(EditorJournal.editor_id == user_id)
    db.execute(delete(EditorJournalPage).where(EditorJournalPage.journal_id.in_(journal_ids)))
    db.execute(delete(EditorJournal).where(EditorJournal.editor_id == user_id))
    for model in (Session, Verification, WebsiteTemplateSelection):
        db.execute(delete(model).where(model.editor_id == user_id))
    db.delete(editor)
    db.commit()
