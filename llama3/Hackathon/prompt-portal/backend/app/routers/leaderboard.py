from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
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
    mode=payload.mode if payload.mode in ("lam","manual") else "manual",
    )
    db.add(s); db.commit(); db.refresh(s)
    return s

@router.get("/", response_model=List[schemas.LeaderboardEntry])
def top_scores(limit: int = 20, skip: int = 0, mode: str | None = Query(default=None), response: Response = None, db: Session = Depends(get_db)):
    # Total number of score rows across all users/templates (used by UI pagination)
    base_q = db.query(models.Score)
    if mode in ("lam","manual"):
        base_q = base_q.filter(models.Score.mode == mode)
    total = base_q.count()

    q = (
        db.query(models.Score, models.User.email, models.PromptTemplate.id, models.PromptTemplate.title)
        .join(models.User, models.Score.user_id == models.User.id)
        .join(models.PromptTemplate, models.Score.template_id == models.PromptTemplate.id)
    )
    if mode in ("lam","manual"):
        q = q.filter(models.Score.mode == mode)
    q = (
        q
        .order_by(models.Score.score.desc(), models.Score.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    results = []
    for idx, (score, email, template_id, title) in enumerate(q, start=1):
        results.append(
            schemas.LeaderboardEntry(
                rank=skip + idx,
                user_email=email,
                template_id=template_id,
                template_title=title,
                score=score.score,
                session_id=score.session_id,
                created_at=score.created_at,
            )
        )

    # Expose total via header for clients to know when to stop fetching
    try:
        if response is not None:
            response.headers["X-Total-Count"] = str(total)
    except Exception:
        pass

    return results

@router.get("/stats")
def leaderboard_stats(db: Session = Depends(get_db)):
    """Return aggregate leaderboard stats.
    - participants: distinct users who submitted at least one score
    - registered_users: total users registered in the system
    """
    participants = db.query(func.count(func.distinct(models.Score.user_id))).scalar() or 0
    registered_users = db.query(func.count(models.User.id)).scalar() or 0
    return { "participants": int(participants), "registered_users": int(registered_users) }
