from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Union
from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])

@router.post("/submit", response_model=schemas.ScoreOut)
def submit_maze_score(payload: schemas.ScoreCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Submit maze game scores (LAM/Manual modes) - NOT for driving game"""
    print("=" * 80)
    print(f"[MAZE SCORE SUBMIT] Received maze game score submission")
    print(f"  User ID: {user.id}")
    print(f"  Template ID: {payload.template_id}")
    print(f"  Mode: {payload.mode}")
    print(f"  Score: {payload.score}, New Score: {payload.new_score}")
    print("=" * 80)
    
    template = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == payload.template_id).first()
    if not template:
        print(f"[MAZE SCORE ERROR] Template {payload.template_id} not found")
        raise HTTPException(404, "Template not found")
    
    # Only accept LAM and Manual modes here (reject driving_game)
    if payload.mode == "driving_game":
        print(f"[MAZE SCORE ERROR] driving_game mode not allowed in this endpoint!")
        raise HTTPException(400, "Use /api/leaderboard/driving-game/submit for driving game scores")
    
    if payload.mode not in ("lam", "manual"):
        print(f"[MAZE SCORE] Invalid mode '{payload.mode}', defaulting to 'manual'")
        payload.mode = "manual"
    
    # Create Maze Game score
    s = models.Score(
        user_id=user.id,
        template_id=payload.template_id,
        session_id=payload.session_id,
        score=payload.score,
        new_score=payload.new_score,
        survival_time=payload.survival_time,
        oxygen_collected=payload.oxygen_collected,
        germs=payload.germs,
        mode=payload.mode,
        total_steps=payload.total_steps,
        optimal_steps=payload.optimal_steps,
        backtrack_count=payload.backtrack_count,
        collision_count=payload.collision_count,
        dead_end_entries=payload.dead_end_entries,
        avg_latency_ms=payload.avg_latency_ms,
        # Clear driving game fields (not used for maze)
        driving_game_consensus_reached=None,
        driving_game_message_count=None,
        driving_game_duration_seconds=None,
        driving_game_player_option=None,
        driving_game_agent_option=None,
    )
    
    db.add(s); db.commit(); db.refresh(s)
    print(f"[MAZE SCORE SUCCESS] Score ID {s.id} saved with mode={s.mode}, score={s.score}")
    return s


@router.post("/driving-game/submit", response_model=schemas.DrivingGameScoreOut)
def submit_driving_game_score(payload: schemas.DrivingGameScoreCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Submit driving game scores - completely separate from maze game scores"""
    print("=" * 80)
    print(f"[DRIVING GAME SUBMIT] Received driving game score submission")
    print(f"  User ID: {user.id}")
    print(f"  Template ID: {payload.template_id}")
    print(f"  Score: {payload.score}")
    print(f"  Messages: {payload.message_count}")
    print(f"  Duration: {payload.duration_seconds}s")
    print(f"  Player: {payload.player_option}, Agent: {payload.agent_option}")
    print("=" * 80)
    
    template = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == payload.template_id).first()
    if not template:
        print(f"[DRIVING GAME ERROR] Template {payload.template_id} not found")
        raise HTTPException(404, "Template not found")
    
    # Create driving game score in separate table
    s = models.DrivingGameScore(
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
    
    db.add(s); db.commit(); db.refresh(s)
    print(f"[DRIVING GAME SUCCESS] Score ID {s.id} saved, score={s.score}")
    return s

@router.get("/", response_model=Union[List[schemas.LeaderboardEntry], List[schemas.DrivingGameLeaderboardEntry]])
def get_leaderboard(limit: int = 20, skip: int = 0, mode: str | None = Query(default=None), response: Response = None, db: Session = Depends(get_db)):
    """Get leaderboard - returns different data structures for maze vs driving game"""
    print("=" * 70)
    print(f"[LEADERBOARD API CALLED]")
    print(f"  mode parameter: '{mode}'")
    print(f"  limit: {limit}, skip: {skip}")
    print("=" * 70)
    
    try:
        # DRIVING GAME: Query separate table
        if mode == "driving_game":
            print(f"[DRIVING GAME MODE] Querying driving_game_scores table")
            
            # Count total driving game scores
            total = db.query(models.DrivingGameScore).count()
            print(f"[DRIVING GAME] Total scores: {total}")
            
            # Query driving game scores
            q = (
                db.query(models.DrivingGameScore, models.User.email, models.PromptTemplate.id, models.PromptTemplate.title)
                .join(models.User, models.DrivingGameScore.user_id == models.User.id)
                .join(models.PromptTemplate, models.DrivingGameScore.template_id == models.PromptTemplate.id)
                .order_by(models.DrivingGameScore.score.desc(), models.DrivingGameScore.created_at.asc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            results = []
            for idx, (score, email, template_id, title) in enumerate(q, start=skip+1):
                results.append(
                    schemas.DrivingGameLeaderboardEntry(
                        rank=idx,
                        user_email=email,
                        template_id=template_id,
                        template_title=title,
                        score=score.score,
                        message_count=score.message_count,
                        duration_seconds=score.duration_seconds,
                        session_id=score.session_id,
                        created_at=score.created_at
                    )
                )
            
            print(f"[DRIVING GAME] Returning {len(results)} scores")
            
            if response is not None:
                response.headers["X-Total-Count"] = str(total)
            
            return results
        
        # MAZE GAME: Query original scores table (LAM/Manual modes)
        print(f"[MAZE GAME MODE] Querying scores table")
        
        base_q = db.query(models.Score)
        if mode in ("lam", "manual"):
            base_q = base_q.filter(models.Score.mode == mode)
            print(f"[FILTER APPLIED] Filtering by mode={mode}")
        else:
            print(f"[NO FILTER] Mode '{mode}' not in allowed list, returning ALL maze scores")
        
        total = base_q.count()
        print(f"[MAZE GAME] Total scores: {total}")

        q = (
            db.query(models.Score, models.User.email, models.PromptTemplate.id, models.PromptTemplate.title)
            .join(models.User, models.Score.user_id == models.User.id)
            .join(models.PromptTemplate, models.Score.template_id == models.PromptTemplate.id)
        )
        if mode in ("lam", "manual"):
            q = q.filter(models.Score.mode == mode)
        
        q = (
            q
            .order_by(models.Score.new_score.desc().nullslast(), models.Score.score.desc(), models.Score.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        results = []
        for idx, (score, email, template_id, title) in enumerate(q, start=skip+1):
            results.append(
                schemas.LeaderboardEntry(
                    rank=idx,
                    user_email=email,
                    template_id=template_id,
                    template_title=title,
                    score=score.score,
                    new_score=score.new_score,
                    session_id=score.session_id,
                    created_at=score.created_at,
                    total_steps=score.total_steps,
                    collision_count=score.collision_count,
                    driving_game_consensus_reached=None,
                    driving_game_message_count=None,
                    driving_game_duration_seconds=None,
                )
            )
        
        print(f"[MAZE GAME] Returning {len(results)} scores")
        
        if response is not None:
            response.headers["X-Total-Count"] = str(total)

        return results
    
    except Exception as e:
        print("=" * 70)
        print(f"[LEADERBOARD ERROR] Exception occurred!")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Error message: {str(e)}")
        import traceback
        print(f"  Traceback:\n{traceback.format_exc()}")
        print("=" * 70)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/stats")
def leaderboard_stats(db: Session = Depends(get_db)):
    """Return aggregate leaderboard stats.
    - participants: distinct users who submitted at least one score
    - registered_users: total users registered in the system
    """
    participants = db.query(func.count(func.distinct(models.Score.user_id))).scalar() or 0
    registered_users = db.query(func.count(models.User.id)).scalar() or 0
    return { "participants": int(participants), "registered_users": int(registered_users) }
