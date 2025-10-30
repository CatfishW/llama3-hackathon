"""
Driving Game Router - Completely separate from leaderboard
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/api/driving", tags=["driving"])


@router.post("/submit", response_model=schemas.DrivingGameScoreOut)
def submit_driving_score(
    payload: schemas.DrivingGameScoreCreate, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    """Submit a driving game score - completely separate system"""
    print("=" * 80)
    print(f"[DRIVING API] Score submission received")
    print(f"  User: {user.id} ({user.email})")
    print(f"  Template: {payload.template_id}")
    print(f"  Score: {payload.score}")
    print(f"  Messages: {payload.message_count}")
    print(f"  Duration: {payload.duration_seconds}s")
    print(f"  Options: Player={payload.player_option}, Agent={payload.agent_option}")
    print("=" * 80)
    
    # Verify template exists
    template = db.query(models.PromptTemplate).filter(
        models.PromptTemplate.id == payload.template_id
    ).first()
    
    if not template:
        print(f"[DRIVING API ERROR] Template {payload.template_id} not found")
        raise HTTPException(404, "Template not found")
    
    # Create driving game score in dedicated table
    driving_score = models.DrivingGameScore(
        user_id=user.id,
        template_id=payload.template_id,
        session_id=payload.session_id,
        score=payload.score,
        consensus_reached=True,
        message_count=payload.message_count,
        duration_seconds=payload.duration_seconds,
        player_option=payload.player_option,
        agent_option=payload.agent_option
    )
    
    db.add(driving_score)
    db.commit()
    db.refresh(driving_score)
    
    print(f"[DRIVING API SUCCESS] Score saved with ID={driving_score.id}")
    
    return driving_score


@router.get("/leaderboard", response_model=List[schemas.DrivingGameLeaderboardEntry])
def get_driving_leaderboard(
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get driving game leaderboard - completely separate from maze leaderboard"""
    print("=" * 80)
    print(f"[DRIVING API] Leaderboard request")
    print(f"  Limit: {limit}, Skip: {skip}")
    print("=" * 80)
    
    # Count total driving game scores
    total = db.query(models.DrivingGameScore).count()
    print(f"[DRIVING API] Total driving scores in database: {total}")
    
    # Query driving game scores with joins
    query = (
        db.query(
            models.DrivingGameScore,
            models.User.email,
            models.PromptTemplate.id,
            models.PromptTemplate.title
        )
        .join(models.User, models.DrivingGameScore.user_id == models.User.id)
        .join(models.PromptTemplate, models.DrivingGameScore.template_id == models.PromptTemplate.id)
        .order_by(
            models.DrivingGameScore.score.desc(),  # Higher score is better
            models.DrivingGameScore.created_at.asc()  # Earlier submission wins ties
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Build response
    results = []
    for idx, (score_obj, user_email, template_id, template_title) in enumerate(query, start=skip+1):
        results.append(
            schemas.DrivingGameLeaderboardEntry(
                rank=idx,
                user_email=user_email,
                template_id=template_id,
                template_title=template_title,
                score=score_obj.score,
                message_count=score_obj.message_count,
                duration_seconds=score_obj.duration_seconds,
                session_id=score_obj.session_id,
                created_at=score_obj.created_at
            )
        )
    
    print(f"[DRIVING API] Returning {len(results)} entries")
    if len(results) > 0:
        print(f"[DRIVING API] Top score: {results[0].score} by {results[0].user_email}")
    
    # Set total count header
    response.headers["X-Total-Count"] = str(total)
    
    return results


@router.get("/stats")
def get_driving_stats(db: Session = Depends(get_db)):
    """Get driving game statistics"""
    print("[DRIVING API] Stats request")
    
    # Count unique participants
    participants = db.query(
        func.count(func.distinct(models.DrivingGameScore.user_id))
    ).scalar() or 0
    
    # Count total registered users
    registered_users = db.query(func.count(models.User.id)).scalar() or 0
    
    # Count total scores
    total_scores = db.query(func.count(models.DrivingGameScore.id)).scalar() or 0
    
    print(f"[DRIVING API] Stats: {participants} participants, {total_scores} scores")
    
    return {
        "participants": int(participants),
        "registered_users": int(registered_users),
        "total_scores": int(total_scores)
    }

