from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas

router = APIRouter(prefix="/api/announcements", tags=["announcements"])

ADMIN_EMAIL = "1819409756@qq.com"


def get_admin_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Dependency to ensure the current user is an admin."""
    if current_user.email != ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can perform this action"
        )
    return current_user


@router.get("/", response_model=List[schemas.AnnouncementOut])
def get_active_announcements(db: Session = Depends(get_db)):
    """Get all active, non-expired announcements. Public endpoint."""
    now = datetime.utcnow()
    announcements = db.query(models.Announcement).filter(
        models.Announcement.is_active == True,
        (models.Announcement.expires_at == None) | (models.Announcement.expires_at > now)
    ).order_by(
        models.Announcement.priority.desc(),
        models.Announcement.created_at.desc()
    ).all()
    return announcements


@router.get("/all", response_model=List[schemas.AnnouncementOut])
def get_all_announcements(
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get all announcements (including inactive and expired). Admin only."""
    announcements = db.query(models.Announcement).order_by(
        models.Announcement.created_at.desc()
    ).all()
    return announcements


@router.post("/", response_model=schemas.AnnouncementOut, status_code=status.HTTP_201_CREATED)
def create_announcement(
    announcement_data: schemas.AnnouncementCreate,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new announcement. Admin only."""
    announcement = models.Announcement(
        title=announcement_data.title,
        content=announcement_data.content,
        announcement_type=announcement_data.announcement_type,
        priority=announcement_data.priority,
        expires_at=announcement_data.expires_at,
        created_by=admin.email,
        is_active=True
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.get("/{announcement_id}", response_model=schemas.AnnouncementOut)
def get_announcement(
    announcement_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific announcement by ID."""
    announcement = db.query(models.Announcement).filter(
        models.Announcement.id == announcement_id
    ).first()
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    return announcement


@router.put("/{announcement_id}", response_model=schemas.AnnouncementOut)
def update_announcement(
    announcement_id: int,
    announcement_data: schemas.AnnouncementUpdate,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update an announcement. Admin only."""
    announcement = db.query(models.Announcement).filter(
        models.Announcement.id == announcement_id
    ).first()
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    # Update fields if provided
    update_data = announcement_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(announcement, field, value)
    
    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: int,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete an announcement. Admin only."""
    announcement = db.query(models.Announcement).filter(
        models.Announcement.id == announcement_id
    ).first()
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    db.delete(announcement)
    db.commit()
    return None


@router.put("/{announcement_id}/toggle", response_model=schemas.AnnouncementOut)
def toggle_announcement(
    announcement_id: int,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle announcement active status. Admin only."""
    announcement = db.query(models.Announcement).filter(
        models.Announcement.id == announcement_id
    ).first()
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    announcement.is_active = not announcement.is_active
    db.commit()
    db.refresh(announcement)
    return announcement
