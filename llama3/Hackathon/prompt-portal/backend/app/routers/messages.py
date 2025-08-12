from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import User, Message, Friendship, FriendshipStatus
from ..schemas import MessageCreate, MessageOut, ConversationOut, UserSearch
from ..deps import get_current_user

router = APIRouter(prefix="/api/messages", tags=["messages"])

@router.get("/conversations", response_model=List[ConversationOut])
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of conversations with last message and unread count"""
    # Get unique users that have messages with current user
    conversations_query = db.query(
        User,
        func.max(Message.created_at).label("last_message_time")
    ).join(
        Message,
        or_(
            and_(Message.sender_id == User.id, Message.recipient_id == current_user.id),
            and_(Message.recipient_id == User.id, Message.sender_id == current_user.id)
        )
    ).filter(
        User.id != current_user.id
    ).group_by(User.id).order_by(desc("last_message_time")).all()
    
    conversations = []
    for user, _ in conversations_query:
        # Get last message
        last_message = db.query(Message).filter(
            or_(
                and_(Message.sender_id == user.id, Message.recipient_id == current_user.id),
                and_(Message.sender_id == current_user.id, Message.recipient_id == user.id)
            )
        ).order_by(desc(Message.created_at)).first()
        
        # Get unread count
        unread_count = db.query(Message).filter(
            and_(
                Message.sender_id == user.id,
                Message.recipient_id == current_user.id,
                Message.is_read == False
            )
        ).count()
        
        conversations.append(ConversationOut(
            user=user,
            last_message=last_message,
            unread_count=unread_count
        ))
    
    return conversations

@router.get("/conversation/{user_id}", response_model=List[MessageOut])
def get_conversation_messages(
    user_id: int,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages in a conversation with a specific user"""
    # Verify users are friends or have previous messages
    friendship = db.query(Friendship).filter(
        and_(
            or_(
                and_(Friendship.requester_id == current_user.id, Friendship.requested_id == user_id),
                and_(Friendship.requester_id == user_id, Friendship.requested_id == current_user.id)
            ),
            Friendship.status == FriendshipStatus.ACCEPTED
        )
    ).first()
    
    if not friendship:
        # Check if they have previous messages
        previous_messages = db.query(Message).filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.recipient_id == user_id),
                and_(Message.sender_id == user_id, Message.recipient_id == current_user.id)
            )
        ).first()
        
        if not previous_messages:
            raise HTTPException(status_code=403, detail="Cannot access conversation")
    
    # Get messages
    messages = db.query(Message).filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.recipient_id == user_id),
            and_(Message.sender_id == user_id, Message.recipient_id == current_user.id)
        )
    ).order_by(desc(Message.created_at)).offset(offset).limit(limit).all()
    
    # Mark messages as read
    db.query(Message).filter(
        and_(
            Message.sender_id == user_id,
            Message.recipient_id == current_user.id,
            Message.is_read == False
        )
    ).update({"is_read": True})
    db.commit()
    
    return messages[::-1]  # Return in chronological order

@router.post("/send", response_model=MessageOut)
def send_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to another user"""
    if message_data.recipient_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot send message to yourself")
    
    # Check if recipient exists
    recipient = db.query(User).filter(User.id == message_data.recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Check if users are friends
    friendship = db.query(Friendship).filter(
        and_(
            or_(
                and_(Friendship.requester_id == current_user.id, Friendship.requested_id == message_data.recipient_id),
                and_(Friendship.requester_id == message_data.recipient_id, Friendship.requested_id == current_user.id)
            ),
            Friendship.status == FriendshipStatus.ACCEPTED
        )
    ).first()
    
    if not friendship:
        raise HTTPException(status_code=403, detail="Can only send messages to friends")
    
    # Create message
    message = Message(
        sender_id=current_user.id,
        recipient_id=message_data.recipient_id,
        content=message_data.content,
        message_type=message_data.message_type
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return message

@router.put("/mark-read/{message_id}")
def mark_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a specific message as read"""
    message = db.query(Message).filter(
        and_(
            Message.id == message_id,
            Message.recipient_id == current_user.id
        )
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.is_read = True
    db.commit()
    
    return {"message": "Message marked as read"}

@router.put("/mark-conversation-read/{user_id}")
def mark_conversation_read(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all messages in a conversation as read"""
    db.query(Message).filter(
        and_(
            Message.sender_id == user_id,
            Message.recipient_id == current_user.id,
            Message.is_read == False
        )
    ).update({"is_read": True})
    
    db.commit()
    
    return {"message": "Conversation marked as read"}

@router.delete("/delete/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a message (only sender can delete)"""
    message = db.query(Message).filter(
        and_(
            Message.id == message_id,
            Message.sender_id == current_user.id
        )
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    db.delete(message)
    db.commit()
    
    return {"message": "Message deleted successfully"}

@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get total unread message count"""
    count = db.query(Message).filter(
        and_(
            Message.recipient_id == current_user.id,
            Message.is_read == False
        )
    ).count()
    
    return {"unread_count": count}

@router.get("/search")
def search_messages(
    q: str = Query(..., min_length=1),
    user_id: Optional[int] = Query(None),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search messages"""
    query = db.query(Message).filter(
        and_(
            or_(
                Message.sender_id == current_user.id,
                Message.recipient_id == current_user.id
            ),
            Message.content.ilike(f"%{q}%")
        )
    )
    
    if user_id:
        query = query.filter(
            or_(
                and_(Message.sender_id == user_id, Message.recipient_id == current_user.id),
                and_(Message.sender_id == current_user.id, Message.recipient_id == user_id)
            )
        )
    
    messages = query.order_by(desc(Message.created_at)).limit(limit).all()
    
    return messages
