from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.database_models import User, Notification
from app.schemas.notification import (
    NotificationListResponse, MarkNotificationReadRequest,
    MarkNotificationReadResponse, MarkAllNotificationsReadResponse
)

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
def get_notifications(
    unread: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch pending notifications (catch-up popup)."""
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.org_id == current_user.org_id
    )

    if unread:
        query = query.filter(Notification.read_at == None)

    notifications = query.order_by(Notification.created_at.desc()).all()

    return {"notifications": notifications}


@router.post("/{id}/read", response_model=MarkNotificationReadResponse)
def mark_notification_read(
    id: str,
    data: MarkNotificationReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == id,
        Notification.user_id == current_user.id,
        Notification.org_id == current_user.org_id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.read_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "message": "Notification marked as read"
    }


@router.post("/read-all", response_model=MarkAllNotificationsReadResponse)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk mark all notifications as read."""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.org_id == current_user.org_id,
        Notification.read_at == None
    ).all()

    count = len(notifications)
    now = datetime.utcnow()

    for notification in notifications:
        notification.read_at = now

    db.commit()

    return {
        "success": True,
        "message": "All notifications marked as read",
        "count": count
    }
