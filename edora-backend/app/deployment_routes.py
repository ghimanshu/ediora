"""Deployment requests are immutable snapshots, never an automatic deployment."""
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import logging
import mimetypes
import re
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import JournalDeployment, EditorJournal, EditorJournalPage, Editor, JournalIssue, JournalArticle, now
from app.journal_routes import own_journal, editor_account, journal_output
from app.routes import current_admin
from app import routes
from app.website_export import build_website_zip
from app.journal_feed_routes import issue_conditions, serialize_issues
from app.config import settings
from app.journal_schemas import JournalOutput

logger = logging.getLogger(__name__)

router=APIRouter(prefix="/api/v1")
class Confirmation(BaseModel):
    expected_updated_at: datetime
    expected_page_count: int = Field(ge=0,le=103)
    model_config=ConfigDict(extra="forbid")


def summary(row):
    return {"id":row.id,"version":row.version,"page_count":row.page_count,"requested_at":row.requested_at,"status":"Requested","preview_path":f"/api/admin/deployments/{row.id}/site/index.html"}

def frozen_zip(db,journal,pages,editor):
    data=build_website_zip(journal,pages,editor.public_code,settings.frontend_url,editor.email)
    issues=db.scalars(select(JournalIssue).where(*issue_conditions(journal.id)).order_by(JournalIssue.published_at.desc(),JournalIssue.id.desc())).all()
    current=next((issue for issue in issues if not issue.is_archived),None)
    archived=[issue for issue in issues if issue.is_archived]
    extra={}
    def feed(selected):
        blocks=[]
        for issue in serialize_issues(db,selected):
            articles=[]
            for article in issue["articles"]:
                record=db.get(JournalArticle,article["id"])
                link=article["article_url"]
                if record.pdf_size:
                    link=f"articles/{record.id}.pdf"
                    extra[link]=record.pdf_content
                pdf=f'<a href="{escape(link,quote=True)}" target="_blank" rel="noopener noreferrer">PDF</a>' if link else ""
                articles.append('<article class="journal-article-row"><div><h3>'+escape(article["title"])+ '</h3><p>'+escape(", ".join(article["authors"]))+'</p><p>'+escape(article["how_to_cite"] or "")+'</p></div>'+pdf+'</article>')
            blocks.append('<section><h2>'+escape(issue["title"])+ ' <small>Vol. '+escape(issue["volume"])+ ' No. '+escape(issue["number"])+ '</small></h2><h3>Articles</h3>'+"".join(articles)+'</section>')
        return "".join(blocks) or '<p>No published volumes available in this version.</p>'
    feeds={"current":feed([current] if current else []),"archives":feed(archived)}
    out=BytesIO()
    with ZipFile(BytesIO(data)) as source,ZipFile(out,"w",ZIP_DEFLATED) as target:
        root=journal.slug+"/"
        count=0
        for name in source.namelist():
            payload=source.read(name)
            if name.endswith('.js'): continue
            if name.endswith('.html'):
                count+=1
                html=payload.decode()
                html=re.sub(r'<script\b[^>]*>.*?</script>', '',html,flags=re.S)
                for kind,content in feeds.items():
                    html=re.sub(r'<section class="journal-live-feed" data-journal-feed="'+kind+r'"[^>]*>.*?</section>',lambda match:content,html,flags=re.S)
                html=re.sub(r'<section data-journal-submission>.*?</section>','<p>Submission form is disabled in this saved deployment preview.</p>',html,flags=re.S)
                payload=html.encode()
            target.writestr(name[len(root):],payload)
        for name,payload in extra.items(): target.writestr(name,payload)
    return out.getvalue(),count

def notify_admin(email, journal_name, version, count, editor_name, journal_id, request_id):
    try:
        routes.send_email(email, f"Deployment requested: {journal_name} V{version}",
                          f"{editor_name} requested deployment of {journal_name} V{version}, with {count} live pages. Review: {settings.frontend_url}/admin/editor-journals/{journal_id}")
    except Exception:
        logger.warning("Deployment request %s saved; admin email delivery failed", request_id)

@router.get("/editor/journal/deployments")
def editor_history(journal_id:int=Query(gt=0),editor:Editor=Depends(editor_account),db:DBSession=Depends(get_db)):
    journal=own_journal(db,editor.id,journal_id)
    return [summary(row) for row in db.scalars(select(JournalDeployment).where(JournalDeployment.journal_id==journal.id).order_by(JournalDeployment.version.desc()))]

@router.post("/editor/journal/deployments",status_code=201)
def request_deployment(data:Confirmation,background_tasks:BackgroundTasks,journal_id:int=Query(gt=0),editor:Editor=Depends(editor_account),db:DBSession=Depends(get_db)):
    journal=own_journal(db,editor.id,journal_id)
    if journal.status!="Published": raise HTTPException(409,"Publish the journal before requesting deployment")
    # Compare the displayed revision after locking the journal; never snapshot unseen edits.
    if journal.updated_at.replace(tzinfo=None)!=data.expected_updated_at.astimezone(timezone.utc).replace(tzinfo=None):
        raise HTTPException(409,"Journal changed; refresh and confirm the latest version")
    pages=db.scalars(select(EditorJournalPage).where(EditorJournalPage.journal_id==journal.id).order_by(EditorJournalPage.position)).all()
    try:
        archive,count=frozen_zip(db,journal,pages,editor)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if count!=data.expected_page_count: raise HTTPException(409,"Page count changed; refresh and confirm again")
    version=(db.scalar(select(func.max(JournalDeployment.version)).where(JournalDeployment.journal_id==journal.id)) or 0)+1
    snapshot=JournalOutput.model_validate(journal_output(db,journal)).model_dump(mode="json")
    row=JournalDeployment(journal_id=journal.id,version=version,page_count=count,snapshot=snapshot,website_zip=archive)
    db.add(row);db.commit();db.refresh(row)
    # The stored request is the durable admin notification; mail is an additional alert.
    admins=db.scalars(select(Editor).where(Editor.role=="super_admin",Editor.is_active.is_(True))).all()
    for admin in admins:
        background_tasks.add_task(notify_admin, admin.email, journal.name, version, count,
                                  f"{editor.first_name} {editor.last_name} ({editor.email})", journal.id, row.id)
    return summary(row)

@router.get("/admin/editor-journals/{journal_id}/deployments")
def admin_history(journal_id:int,admin:Editor=Depends(current_admin),db:DBSession=Depends(get_db)):
    if not db.get(EditorJournal,journal_id): raise HTTPException(404,"Journal not found")
    return [summary(row) for row in db.scalars(select(JournalDeployment).where(JournalDeployment.journal_id==journal_id).order_by(JournalDeployment.version.desc()))]

@router.get("/admin/deployments/{deployment_id}/site/{file_path:path}")
def preview_version(deployment_id:int,file_path:str,admin:Editor=Depends(current_admin),db:DBSession=Depends(get_db)):
    row=db.get(JournalDeployment,deployment_id)
    if not row: raise HTTPException(404,"Version not found")
    if not file_path or any(part in {"..","."} for part in file_path.split("/")): raise HTTPException(404,"File not found")
    with ZipFile(BytesIO(row.website_zip)) as archive:
        if file_path not in archive.namelist(): raise HTTPException(404,"File not found")
        payload=archive.read(file_path)
    content_type=mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return Response(payload,media_type=content_type,headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Content-Security-Policy":"default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'; sandbox allow-same-origin allow-popups"})
