from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/api/templates", tags=["templates"])

@router.post("/", response_model=schemas.TemplateOut)
def create_template(payload: schemas.TemplateCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    t = models.PromptTemplate(
        user_id=user.id,
        title=payload.title,
        description=payload.description or "",
        content=payload.content,
        is_active=payload.is_active,
        version=payload.version or 1,
    )
    db.add(t); db.commit(); db.refresh(t)
    return t

@router.get("/", response_model=List[schemas.TemplateOut])
def list_templates(skip:int=0, limit:int=50, mine: bool=True, db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(models.PromptTemplate)
    if mine:
        q = q.filter(models.PromptTemplate.user_id == user.id)
    return q.order_by(models.PromptTemplate.updated_at.desc()).offset(skip).limit(limit).all()

@router.get("/{template_id}", response_model=schemas.TemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    t = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == template_id, models.PromptTemplate.user_id == user.id).first()
    if not t:
        raise HTTPException(404, "Template not found")
    return t

# Public read-only access for viewing templates from the leaderboard
@router.get("/public/{template_id}", response_model=schemas.TemplateOut)
def get_template_public(template_id: int, db: Session = Depends(get_db)):
    t = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == template_id).first()
    if not t:
        raise HTTPException(404, "Template not found")
    return t

@router.patch("/{template_id}", response_model=schemas.TemplateOut)
def update_template(template_id: int, payload: schemas.TemplateUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    t = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == template_id, models.PromptTemplate.user_id == user.id).first()
    if not t: raise HTTPException(404, "Template not found")
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(t, k, v)
    db.commit(); db.refresh(t)
    return t

@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    t = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == template_id, models.PromptTemplate.user_id == user.id).first()
    if not t: raise HTTPException(404, "Template not found")
    # Delete dependent scores first to avoid FK constraint violations
    try:
        db.query(models.Score).filter(models.Score.template_id == t.id).delete(synchronize_session=False)
        db.delete(t)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"ok": True}
