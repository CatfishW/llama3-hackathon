from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import User, Friendship, FriendshipStatus
from ..schemas import FriendshipCreate, FriendshipRespond, FriendshipOut, FriendOut, UserSearch
from ..deps import get_current_user

router = APIRouter(prefix="/api/friends", tags=["friends"])

@router.get("/search", response_model=List[UserSearch])
def search_users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search for users by name or email"""
    users = db.query(User).filter(
        and_(
            User.id != current_user.id,
            User.profile_visible == True,
            or_(
                User.full_name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%")
            )
        )
    ).limit(20).all()
    
    # Check for pending requests and add the field
    result = []
    for user in users:
        # Check if there's a pending request from current user to this user
        pending_request = db.query(Friendship).filter(
            and_(
                Friendship.requester_id == current_user.id,
                Friendship.requested_id == user.id,
                Friendship.status == FriendshipStatus.PENDING
            )
        ).first()
        
        user_dict = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "profile_picture": user.profile_picture,
            "level": user.level,
            "is_online": user.is_online,
            "has_pending_request": pending_request is not None
        }
        result.append(user_dict)
    
    return result

@router.get("/", response_model=List[FriendshipOut])
@router.get("", response_model=List[FriendshipOut])
def get_friends_root(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all friendships (friends + pending requests) for current user"""
    friendships = db.query(Friendship).options(
        joinedload(Friendship.requester),
        joinedload(Friendship.requested)
    ).filter(
        or_(
            Friendship.requester_id == current_user.id,
            Friendship.requested_id == current_user.id
        )
    ).all()
    
    return friendships

@router.post("/request", response_model=dict)
def send_friend_request(
    request_data: FriendshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a friend request"""
    print(f"[DEBUG] Friend request: user {current_user.id} -> user {request_data.requested_id}")
    
    if request_data.requested_id == current_user.id:
        print(f"[DEBUG] Error: User trying to add themselves")
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")
    
    # Check if user exists and allows friend requests
    requested_user = db.query(User).filter(User.id == request_data.requested_id).first()
    if not requested_user:
        print(f"[DEBUG] Error: User {request_data.requested_id} not found")
        raise HTTPException(status_code=404, detail="User not found")
    
    if not requested_user.allow_friend_requests:
        print(f"[DEBUG] Error: User {request_data.requested_id} doesn't accept friend requests")
        raise HTTPException(status_code=400, detail="User does not accept friend requests")
    
    # Check if friendship already exists
    existing_friendship = db.query(Friendship).filter(
        or_(
            and_(
                Friendship.requester_id == current_user.id,
                Friendship.requested_id == request_data.requested_id
            ),
            and_(
                Friendship.requester_id == request_data.requested_id,
                Friendship.requested_id == current_user.id
            )
        )
    ).first()
    
    if existing_friendship:
        print(f"[DEBUG] Existing friendship found: status={existing_friendship.status}")
        if existing_friendship.status == FriendshipStatus.ACCEPTED:
            raise HTTPException(status_code=400, detail="Already friends with this user")
        elif existing_friendship.status == FriendshipStatus.PENDING:
            # Check who sent the original request
            if existing_friendship.requester_id == current_user.id:
                raise HTTPException(status_code=400, detail="Friend request already sent to this user")
            else:
                raise HTTPException(status_code=400, detail="This user has already sent you a friend request")
        elif existing_friendship.status == FriendshipStatus.BLOCKED:
            raise HTTPException(status_code=400, detail="Cannot send friend request to this user")
    
    # Create friendship
    print(f"[DEBUG] Creating new friendship")
    friendship = Friendship(
        requester_id=current_user.id,
        requested_id=request_data.requested_id,
        status=FriendshipStatus.PENDING
    )
    
    db.add(friendship)
    db.commit()
    
    print(f"[DEBUG] Friend request sent successfully")
    return {"message": "Friend request sent successfully"}

@router.get("/requests", response_model=List[FriendshipOut])
def get_friend_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending friend requests received by current user"""
    requests = db.query(Friendship).options(
        joinedload(Friendship.requester),
        joinedload(Friendship.requested)
    ).filter(
        and_(
            Friendship.requested_id == current_user.id,
            Friendship.status == FriendshipStatus.PENDING
        )
    ).all()
    
    return requests

@router.get("/sent-requests", response_model=List[FriendshipOut])
def get_sent_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get friend requests sent by current user"""
    requests = db.query(Friendship).filter(
        and_(
            Friendship.requester_id == current_user.id,
            Friendship.status == FriendshipStatus.PENDING
        )
    ).all()
    
    return requests

@router.put("/accept/{friendship_id}")
def accept_friend_request(
    friendship_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a friend request"""
    friendship = db.query(Friendship).filter(
        and_(
            Friendship.id == friendship_id,
            Friendship.requested_id == current_user.id,
            Friendship.status == FriendshipStatus.PENDING
        )
    ).first()
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    friendship.status = FriendshipStatus.ACCEPTED
    friendship.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Friend request accepted"}

@router.put("/reject/{friendship_id}")
def reject_friend_request(
    friendship_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a friend request"""
    friendship = db.query(Friendship).filter(
        and_(
            Friendship.id == friendship_id,
            Friendship.requested_id == current_user.id,
            Friendship.status == FriendshipStatus.PENDING
        )
    ).first()
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    db.delete(friendship)
    db.commit()
    
    return {"message": "Friend request rejected"}

@router.post("/respond")
def respond_to_friend_request(
    response_data: FriendshipRespond,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept or reject a friend request"""
    print(f"[DEBUG] Friend response: user {response_data.user_id} -> current user {current_user.id}, accept={response_data.accept}")
    
    # Find the friendship where the current user is the requested user and the sender is user_id
    friendship = db.query(Friendship).filter(
        and_(
            Friendship.requester_id == response_data.user_id,
            Friendship.requested_id == current_user.id,
            Friendship.status == FriendshipStatus.PENDING
        )
    ).first()
    
    if not friendship:
        print(f"[DEBUG] Friend request not found")
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    if response_data.accept:
        friendship.status = FriendshipStatus.ACCEPTED
        message = "Friend request accepted"
        print(f"[DEBUG] Accepted friend request")
    else:
        db.delete(friendship)
        message = "Friend request rejected"
        print(f"[DEBUG] Rejected friend request")
    
    db.commit()
    return {"message": message}

@router.delete("/cancel/{friendship_id}")
def cancel_friend_request(
    friendship_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a sent friend request"""
    friendship = db.query(Friendship).filter(
        and_(
            Friendship.id == friendship_id,
            Friendship.requester_id == current_user.id,
            Friendship.status == FriendshipStatus.PENDING
        )
    ).first()
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    db.delete(friendship)
    db.commit()
    
    return {"message": "Friend request cancelled"}

@router.get("/list", response_model=List[FriendOut])
def get_friends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of accepted friends"""
    friendships = db.query(Friendship).filter(
        and_(
            or_(
                Friendship.requester_id == current_user.id,
                Friendship.requested_id == current_user.id
            ),
            Friendship.status == FriendshipStatus.ACCEPTED
        )
    ).all()
    
    friends = []
    for friendship in friendships:
        if friendship.requester_id == current_user.id:
            friend = friendship.requested
        else:
            friend = friendship.requester
        friends.append(friend)
    
    return friends

@router.delete("/remove/{friend_id}")
def remove_friend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a friend"""
    friendship = db.query(Friendship).filter(
        and_(
            or_(
                and_(
                    Friendship.requester_id == current_user.id,
                    Friendship.requested_id == friend_id
                ),
                and_(
                    Friendship.requester_id == friend_id,
                    Friendship.requested_id == current_user.id
                )
            ),
            Friendship.status == FriendshipStatus.ACCEPTED
        )
    ).first()
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friendship not found")
    
    db.delete(friendship)
    db.commit()
    
    return {"message": "Friend removed successfully"}

@router.put("/block/{user_id}")
def block_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Block a user"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    
    # Check if friendship exists
    friendship = db.query(Friendship).filter(
        or_(
            and_(
                Friendship.requester_id == current_user.id,
                Friendship.requested_id == user_id
            ),
            and_(
                Friendship.requester_id == user_id,
                Friendship.requested_id == current_user.id
            )
        )
    ).first()
    
    if friendship:
        friendship.status = FriendshipStatus.BLOCKED
        friendship.updated_at = datetime.utcnow()
    else:
        # Create a new blocked relationship
        friendship = Friendship(
            requester_id=current_user.id,
            requested_id=user_id,
            status=FriendshipStatus.BLOCKED
        )
        db.add(friendship)
    
    db.commit()
    return {"message": "User blocked successfully"}

@router.get("/suggestions", response_model=List[UserSearch])
def get_friend_suggestions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get friend suggestions based on mutual connections"""
    # Get current friends
    current_friends = db.query(Friendship).filter(
        and_(
            or_(
                Friendship.requester_id == current_user.id,
                Friendship.requested_id == current_user.id
            ),
            Friendship.status == FriendshipStatus.ACCEPTED
        )
    ).all()
    
    friend_ids = set()
    for friendship in current_friends:
        if friendship.requester_id == current_user.id:
            friend_ids.add(friendship.requested_id)
        else:
            friend_ids.add(friendship.requester_id)
    
    # Get users that are not current friends and have public profiles
    excluded_ids = friend_ids.copy()
    excluded_ids.add(current_user.id)
    
    suggestions = db.query(User).filter(
        and_(
            ~User.id.in_(excluded_ids),
            User.profile_visible == True,
            User.allow_friend_requests == True
        )
    ).limit(10).all()
    
    return suggestions
