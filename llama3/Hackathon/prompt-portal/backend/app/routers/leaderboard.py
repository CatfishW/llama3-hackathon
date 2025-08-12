from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])

@router.post("/submit", response_model=schemas.ScoreOut)
def submit_score(payload: schemas.ScoreCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    template = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == payload.template_id).first()
    if not template:
        raise HTTPException(404, "Template not found")
    s = models.Score(
        user_id=user.id,
        template_id=payload.template_id,
        session_id=payload.session_id,
        score=payload.score,
        survival_time=payload.survival_time,
        oxygen_collected=payload.oxygen_collected,
        germs=payload.germs,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s

@router.get("/", response_model=List[schemas.LeaderboardEntry])
def top_scores(limit: int = 20, db: Session = Depends(get_db)):
    q = (
        db.query(models.Score, models.User.email, models.PromptTemplate.title)
        .join(models.User, models.Score.user_id == models.User.id)
        .join(models.PromptTemplate, models.Score.template_id == models.PromptTemplate.id)
        .order_by(models.Score.score.desc(), models.Score.created_at.asc())
        .limit(limit)
        .all()
    )
    results = []
    for idx, (score, email, title) in enumerate(q, start=1):
        results.append(
            schemas.LeaderboardEntry(
                rank=idx,
                user_email=email,
                template_title=title,
                score=score.score,
                session_id=score.session_id,
                created_at=score.created_at,
            )
        )
    return results
