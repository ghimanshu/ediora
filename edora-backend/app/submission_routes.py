import base64
import binascii
import hashlib
import hmac
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import Editor, EditorJournal, SubmissionCaptcha, JournalArticle, now
from app.emails import send_manuscript_email
router = APIRouter(prefix="/api/v1/public/journals")

def published_journal(db, editor_code, journal_slug):
    result = db.execute(select(EditorJournal, Editor).join(Editor, Editor.id == EditorJournal.editor_id).where(Editor.public_code == editor_code, EditorJournal.slug == journal_slug, EditorJournal.status == "Published", Editor.is_active.is_(True), Editor.is_verified.is_(True), Editor.role == "editor")).first()
    if not result:
        raise HTTPException(404, "Published journal not found")
    return result

def challenge_hash(token, answer):
    return hashlib.sha256((token + answer.strip().upper()).encode()).hexdigest()

class SubmissionInput(BaseModel):
    full_name: str = Field(min_length=1,max_length=150)
    email: EmailStr
    title: str = Field(min_length=1,max_length=300)
    authors: str = Field(min_length=1,max_length=2000)
    abstract: str = Field(min_length=10,max_length=10000)
    pdf_base64: str = Field(min_length=1,max_length=13981020)
    captcha_id: str = Field(min_length=32,max_length=64)
    captcha_answer: str = Field(min_length=1,max_length=12)
    model_config = ConfigDict(extra="forbid",str_strip_whitespace=True)
    @field_validator("full_name", "email")
    @classmethod
    def no_header_newlines(cls,value):
        if "\r" in value or "\n" in value:
            raise ValueError("Use a single line")
        return value

@router.get("/{editor_code}/{journal_slug}/submission/captcha")
def captcha(editor_code: str = Path(pattern=r"^[a-z0-9]{8}$"), journal_slug: str = Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",max_length=150), db: DBSession = Depends(get_db)):
    journal, _ = published_journal(db,editor_code,journal_slug)
    db.execute(delete(SubmissionCaptcha).where(SubmissionCaptcha.expires_at < now()))
    count = db.scalar(select(func.count()).select_from(SubmissionCaptcha).where(SubmissionCaptcha.journal_id == journal.id,SubmissionCaptcha.created_at > now()-timedelta(minutes=10)))
    if count >= 100:
        db.commit()
        raise HTTPException(429,"Too many verification requests. Try again later.")
    token=secrets.token_hex(24)
    answer="".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    db.add(SubmissionCaptcha(id=token,journal_id=journal.id,answer_hash=challenge_hash(token,answer),expires_at=now()+timedelta(minutes=10)))
    db.commit()
    letters="".join(f'<text x="{18+i*27}" y="37" transform="rotate({secrets.randbelow(15)-7} {18+i*27} 37)">{char}</text>' for i,char in enumerate(answer))
    noise="".join(f'<path d="M0 {secrets.randbelow(55)} L190 {secrets.randbelow(55)}" stroke="#a2b8ac"/>' for _ in range(5))
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="190" height="55" viewBox="0 0 190 55"><rect width="190" height="55" fill="#eef3f0"/>{noise}<g font-family="monospace" font-size="29" font-weight="bold" fill="#214d3e">{letters}</g></svg>'
    return {"captcha_id":token,"image":"data:image/svg+xml;base64,"+base64.b64encode(svg.encode()).decode(),"expires_in":600}

@router.post("/{editor_code}/{journal_slug}/submission",status_code=201)
def submit(data: SubmissionInput, editor_code: str = Path(pattern=r"^[a-z0-9]{8}$"),journal_slug: str = Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",max_length=150),db: DBSession=Depends(get_db)):
    journal, editor = published_journal(db,editor_code,journal_slug)
    try:
        pdf=base64.b64decode(data.pdf_base64,validate=True)
    except (ValueError,binascii.Error):
        raise HTTPException(422,"Invalid PDF upload")
    if len(pdf)>10*1024*1024:
        raise HTTPException(413,"PDF must not exceed 10 MB")
    if not pdf.startswith(b"%PDF-") or b"%%EOF" not in pdf[-2048:]:
        raise HTTPException(422,"Upload a valid PDF document")
    # Lock the parent first so CAPTCHA/rate checks and deletion use the same lock order.
    db.scalar(select(EditorJournal.id).where(EditorJournal.id==journal.id).with_for_update())
    challenge=db.scalar(select(SubmissionCaptcha).where(SubmissionCaptcha.id==data.captcha_id,SubmissionCaptcha.journal_id==journal.id,SubmissionCaptcha.expires_at>now()).with_for_update())
    if not challenge:
        raise HTTPException(422,"CAPTCHA expired or already used. Refresh it and try again.")
    valid=hmac.compare_digest(challenge.answer_hash,challenge_hash(data.captcha_id,data.captcha_answer))
    db.delete(challenge)
    if not valid:
        db.commit()
        raise HTTPException(422,"Incorrect CAPTCHA. Enter the new code and try again.")
    count=db.scalar(select(func.count()).select_from(JournalArticle).where(JournalArticle.journal_id==journal.id,JournalArticle.submitter_email==str(data.email),JournalArticle.created_at>now()-timedelta(hours=1)))
    if count>=5:
        db.commit()
        raise HTTPException(429,"Submission limit reached. Please try again later.")
    import re
    authors=[name.strip() for name in re.split(r"[,;\n]+",data.authors) if name.strip()]
    if not 1 <= len(authors) <= 50 or any(len(name)>120 for name in authors):
        db.commit()
        raise HTTPException(422,"Provide up to 50 author names, each no longer than 120 characters.")
    record=JournalArticle(journal_id=journal.id,submitter_name=data.full_name,submitter_email=str(data.email),title=data.title,authors=authors,abstract=data.abstract,pdf_content=pdf,pdf_size=len(pdf),pdf_filename="manuscript.pdf",status="Submitted",is_published=False)
    db.add(record)
    db.commit()
    try:
        send_manuscript_email(editor.email,journal.name,record)
    except Exception:
        return {"message":"Your manuscript was received. The editor notification is pending.","reference":record.id}
    record.notification_sent=True
    db.commit()
    return {"message":"Your manuscript has been submitted to the editor.","reference":record.id}
