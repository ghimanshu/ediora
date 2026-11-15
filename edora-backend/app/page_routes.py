from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from app.database import get_db
from app.models import Editor, WebPage
from app.page_schemas import PageInput, PageOutput, PageSummary
from app.routes import current_admin

router = APIRouter(prefix="/api/v1/admin/pages")

def find_page(db, page_id):
    page = db.get(WebPage, page_id)
    if not page:
        raise HTTPException(404, "Page not found")
    return page

def save_page(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A page with this URL slug already exists")

@router.get("", response_model=list[PageSummary])
def list_pages(admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    return db.scalars(select(WebPage).order_by(WebPage.id.desc())).all()

@router.get("/{page_id}", response_model=PageOutput)
def get_page(page_id: int, admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    return find_page(db, page_id)

@router.post("", response_model=PageOutput, status_code=201)
def create_page(data: PageInput, admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    page = WebPage(**data.model_dump())
    db.add(page)
    save_page(db)
    return page

@router.patch("/{page_id}", response_model=PageOutput)
def edit_page(page_id: int, data: PageInput, admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    page = find_page(db, page_id)
    for key, value in data.model_dump().items():
        setattr(page, key, value)
    save_page(db)
    return page

@router.delete("/{page_id}", status_code=204)
def delete_page(page_id: int, admin: Editor = Depends(current_admin), db: DBSession = Depends(get_db)):
    db.delete(find_page(db, page_id))
    db.commit()
