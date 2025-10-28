from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import get_db
from ..models import PromptTemplate


router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("/", response_model=List[schemas.TemplateOut])
def list_templates(db: Session = Depends(get_db)) -> List[schemas.TemplateOut]:
    templates = db.query(PromptTemplate).order_by(PromptTemplate.updated_at.desc()).all()
    return [schemas.TemplateOut.model_validate(t, from_attributes=True) for t in templates]


@router.post("/", response_model=schemas.TemplateOut)
def create_template(payload: schemas.TemplateCreate, db: Session = Depends(get_db)) -> schemas.TemplateOut:
    now = datetime.utcnow()
    tpl = PromptTemplate(
        user_id=None,  # Explicitly set to None for now (no auth)
        title=payload.title,
        description=payload.description or "",
        content=payload.content,
        is_active=1 if payload.is_active else 0,
        version=payload.version or 1,
        created_at=now,
        updated_at=now,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return schemas.TemplateOut.model_validate(tpl, from_attributes=True)


@router.patch("/{template_id}", response_model=schemas.TemplateOut)
def update_template(template_id: int, payload: schemas.TemplateUpdate, db: Session = Depends(get_db)) -> schemas.TemplateOut:
    tpl: Optional[PromptTemplate] = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    if payload.title is not None:
        tpl.title = payload.title
    if payload.description is not None:
        tpl.description = payload.description
    if payload.content is not None:
        tpl.content = payload.content
    if payload.is_active is not None:
        tpl.is_active = 1 if payload.is_active else 0
    if payload.version is not None:
        tpl.version = payload.version

    tpl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tpl)
    return schemas.TemplateOut.model_validate(tpl, from_attributes=True)


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)) -> dict:
    tpl: Optional[PromptTemplate] = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(tpl)
    db.commit()
    return {"ok": True}


