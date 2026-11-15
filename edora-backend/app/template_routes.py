from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import Editor, WebsiteTemplate, WebsiteTemplateSelection
from app.routes import current_admin, current_editor
from app.template_schemas import TemplateInput, TemplateOutput, TemplateChoice

router = APIRouter(prefix="/api/v1")

@router.get("/admin/templates", response_model=list[TemplateOutput])
def admin_templates(admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    return db.scalars(select(WebsiteTemplate).order_by(WebsiteTemplate.id)).all()

@router.post("/admin/templates", response_model=TemplateOutput, status_code=201)
def create_template(data: TemplateInput, admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    template = WebsiteTemplate(**data.model_dump())
    db.add(template)
    save_template(db)
    return template

@router.patch("/admin/templates/{template_id}", response_model=TemplateOutput)
def edit_template(template_id: int, data: TemplateInput, admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    template = db.get(WebsiteTemplate, template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    for key, value in data.model_dump().items():
        setattr(template, key, value)
    save_template(db)
    return template

def save_template(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A template with this name already exists")

@router.delete("/admin/templates/{template_id}", status_code=204)
def delete_template(template_id: int, admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    template = db.scalar(select(WebsiteTemplate).where(WebsiteTemplate.id == template_id).with_for_update())
    if not template:
        raise HTTPException(404, "Template not found")
    if db.scalar(select(WebsiteTemplateSelection.editor_id).where(WebsiteTemplateSelection.template_id == template_id).limit(1)):
        raise HTTPException(409, "This template is selected by users. Choose another template for those accounts before deleting it.")
    db.delete(template)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This template is selected by users and cannot be deleted.")

@router.get("/templates", response_model=list[TemplateOutput])
def available_templates(editor: Editor = Depends(current_editor), db: DBSession = Depends(get_db)):
    return db.scalars(select(WebsiteTemplate).order_by(WebsiteTemplate.id)).all()

@router.get("/website/template", response_model=TemplateOutput | None)
def selected_template(editor: Editor = Depends(current_editor), db: DBSession = Depends(get_db)):
    selection = db.get(WebsiteTemplateSelection, editor.id)
    return db.get(WebsiteTemplate, selection.template_id) if selection else None

@router.post("/website/template", response_model=TemplateOutput)
def choose_template(data: TemplateChoice, editor: Editor = Depends(current_editor), db: DBSession = Depends(get_db)):
    # Lock the account to serialize simultaneous first-time selections.
    db.scalar(select(Editor).where(Editor.id == editor.id).with_for_update())
    template = db.scalar(select(WebsiteTemplate).where(WebsiteTemplate.id == data.template_id).with_for_update())
    if not template:
        raise HTTPException(404, "Template not found")
    selection = db.get(WebsiteTemplateSelection, editor.id)
    if selection:
        selection.template_id = template.id
    else:
        db.add(WebsiteTemplateSelection(editor_id=editor.id, template_id=template.id))
    db.commit()
    return template
