from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List
import json
import jwt
from datetime import datetime

from .config import settings
from .database import get_db
from .models import User, Message, Friendship, FriendshipStatus
from sqlalchemy.orm import Session

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Update user online status
        # Note: You'd need to inject the database session here in a real implementation
        print(f"User {user_id} connected via WebSocket")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"User {user_id} disconnected from WebSocket")
    
    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(message)
                except:
                    # Connection is broken, remove it
                    self.active_connections[user_id].remove(websocket)
    
    async def send_to_friends(self, message: str, user_id: int, friend_ids: List[int]):
        for friend_id in friend_ids:
            await self.send_personal_message(message, friend_id)

manager = ConnectionManager()

async def get_current_user_ws(websocket: WebSocket, token: str, db: Session):
    """Authenticate WebSocket connection"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            await websocket.close(code=1008, reason="Invalid token")
            return None
    except jwt.PyJWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        await websocket.close(code=1008, reason="User not found")
        return None
    
    return user

async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time messaging"""
    db = next(get_db())
    user = await get_current_user_ws(websocket, token, db)
    
    if not user:
        return
    
    await manager.connect(websocket, user.id)
    
    # Update user online status
    user.is_online = True
    user.last_seen = datetime.utcnow()
    db.commit()
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data["type"] == "send_message":
                await handle_send_message(message_data, user, db)
            elif message_data["type"] == "typing":
                await handle_typing(message_data, user, db)
            elif message_data["type"] == "mark_read":
                await handle_mark_read(message_data, user, db)
            elif message_data["type"] == "online_status":
                await handle_online_status(message_data, user, db)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
        
        # Update user offline status
        user.is_online = False
        user.last_seen = datetime.utcnow()
        db.commit()
        
        # Notify friends about offline status
        await notify_friends_status_change(user, db, "offline")
    
    finally:
        db.close()

async def handle_send_message(message_data: dict, sender: User, db: Session):
    """Handle sending a message via WebSocket"""
    recipient_id = message_data.get("recipient_id")
    content = message_data.get("content")
    message_type = message_data.get("message_type", "text")
    
    if not recipient_id or not content:
        return
    
    # Verify friendship
    friendship = db.query(Friendship).filter(
        Friendship.status == FriendshipStatus.ACCEPTED,
        ((Friendship.requester_id == sender.id) & (Friendship.requested_id == recipient_id)) |
        ((Friendship.requester_id == recipient_id) & (Friendship.requested_id == sender.id))
    ).first()
    
    if not friendship:
        return
    
    # Create message
    message = Message(
        sender_id=sender.id,
        recipient_id=recipient_id,
        content=content,
        message_type=message_type
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Send to recipient if online
    notification = {
        "type": "new_message",
        "message": {
            "id": message.id,
            "sender_id": message.sender_id,
            "recipient_id": message.recipient_id,
            "content": message.content,
            "message_type": message.message_type,
            "created_at": message.created_at.isoformat(),
            "sender": {
                "id": sender.id,
                "email": sender.email,
                "full_name": sender.full_name,
                "profile_picture": sender.profile_picture
            }
        }
    }
    
    await manager.send_personal_message(json.dumps(notification), recipient_id)

async def handle_typing(message_data: dict, user: User, db: Session):
    """Handle typing indicator"""
    recipient_id = message_data.get("recipient_id")
    is_typing = message_data.get("is_typing", False)
    
    if not recipient_id:
        return
    
    notification = {
        "type": "typing",
        "user_id": user.id,
        "is_typing": is_typing
    }
    
    await manager.send_personal_message(json.dumps(notification), recipient_id)

async def handle_mark_read(message_data: dict, user: User, db: Session):
    """Handle marking messages as read"""
    sender_id = message_data.get("sender_id")
    
    if not sender_id:
        return
    
    # Mark messages as read
    db.query(Message).filter(
        Message.sender_id == sender_id,
        Message.recipient_id == user.id,
        Message.is_read == False
    ).update({"is_read": True})
    db.commit()
    
    # Notify sender about read status
    notification = {
        "type": "messages_read",
        "reader_id": user.id
    }
    
    await manager.send_personal_message(json.dumps(notification), sender_id)

async def handle_online_status(message_data: dict, user: User, db: Session):
    """Handle online status updates"""
    is_online = message_data.get("is_online", True)
    
    user.is_online = is_online
    user.last_seen = datetime.utcnow()
    db.commit()
    
    status = "online" if is_online else "offline"
    await notify_friends_status_change(user, db, status)

async def notify_friends_status_change(user: User, db: Session, status: str):
    """Notify friends about user's status change"""
    if not user.show_online_status:
        return
    
    # Get friend IDs
    friendships = db.query(Friendship).filter(
        Friendship.status == FriendshipStatus.ACCEPTED,
        ((Friendship.requester_id == user.id) | (Friendship.requested_id == user.id))
    ).all()
    
    friend_ids = []
    for friendship in friendships:
        if friendship.requester_id == user.id:
            friend_ids.append(friendship.requested_id)
        else:
            friend_ids.append(friendship.requester_id)
    
    notification = {
        "type": "friend_status_change",
        "user_id": user.id,
        "status": status,
        "last_seen": user.last_seen.isoformat()
    }
    
    for friend_id in friend_ids:
        await manager.send_personal_message(json.dumps(notification), friend_id)
