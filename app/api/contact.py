"""
Contact endpoints - WhatsApp links and contact logging (Issues #11 & #12).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
from uuid import UUID
import urllib.parse
from datetime import datetime

from app.db import get_db
from app.db.models import User, Parent, Tutor, ContactLog
from app.schemas.contact import (
    WhatsAppLinkResponse,
    ContactLogRequest,
    ContactLogResponse
)
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["Contact"])

CurrentUserDep = Depends(get_current_user)
DBDep = Depends(get_db)


@router.get("/whatsapp/{user_id}", response_model=WhatsAppLinkResponse)
async def get_whatsapp_link(
    user_id: UUID,
    current_user: dict = CurrentUserDep,
    db: Session = DBDep,
):
    """
    Get WhatsApp contact link for a user (Issue #11).

    This is the CONVERSION MOMENT - allows users to contact each other.

    Workflow:
    1. Verify target user exists and is onboarded
    2. Check if WhatsApp is enabled for target user
    3. Get WhatsApp number from parent/tutor profile
    4. Generate wa.me link with prefilled message
    5. Optionally log contact attempt (Issue #12)

    Args:
        user_id: Target user to contact
        current_user: Authenticated user making request
        db: Database session

    Returns:
        WhatsAppLinkResponse with wa.me deep link

    Raises:
        HTTPException 400: Cannot contact yourself
        HTTPException 404: User not found or WhatsApp not enabled
    """
    requesting_user_id = current_user['user_id']

    # Prevent self-contact
    if str(user_id) == requesting_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot contact yourself"
        )

    # Get target user
    user = db.query(User).filter(
        and_(
            User.id == user_id,
            User.onboarded.is_(True),
            User.is_active.is_(True)
        )
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or not available"
        )

    # Get WhatsApp info based on role
    whatsapp_number = None
    whatsapp_enabled = False

    if user.role == "parent":
        parent = db.query(Parent).filter(Parent.user_id == user.id).first()
        if parent:
            whatsapp_number = parent.whatsapp_number
            whatsapp_enabled = parent.whatsapp_enabled

    elif user.role == "tutor":
        tutor = db.query(Tutor).filter(Tutor.user_id == user.id).first()
        if tutor:
            whatsapp_number = tutor.whatsapp_number
            whatsapp_enabled = tutor.whatsapp_enabled

    # Check if WhatsApp is enabled
    if not whatsapp_enabled or not whatsapp_number:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WhatsApp contact not available for this user"
        )

    # Get requesting user's name for personalized message
    requesting_user = db.query(User).filter(User.id == requesting_user_id).first()
    requester_name = requesting_user.name.split()[0] if requesting_user else "Someone"

    # Get target user's first name
    target_first_name = user.name.split()[0] if user.name else "there"

    # Create prefilled message
    app_name = "Homeschool Connect"  # You can make this configurable
    prefilled_message = (
        f"Hi {target_first_name}, I'm {requester_name}. "
        f"I found you on {app_name} and would love to connect!"
    )

    # Clean phone number (remove spaces, dashes, etc.)
    clean_number = whatsapp_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    # Ensure number starts with + (international format)
    if not clean_number.startswith("+"):
        logger.warning(f"Phone number {whatsapp_number} doesn't start with +. Adding it.")
        clean_number = "+" + clean_number

    # URL encode the message
    encoded_message = urllib.parse.quote(prefilled_message)

    # Generate wa.me link
    whatsapp_url = f"https://wa.me/{clean_number}?text={encoded_message}"

    logger.info(
        f"WhatsApp link generated: {requesting_user_id} -> {user_id} "
        f"(phone: {clean_number[:5]}...)"
    )

    return WhatsAppLinkResponse(
        whatsapp_url=whatsapp_url,
        phone_number=clean_number,
        prefilled_message=prefilled_message,
        user_name=user.name
    )


@router.post("/log", response_model=ContactLogResponse)
async def log_contact_attempt(
    log_data: ContactLogRequest,
    current_user: dict = CurrentUserDep,
    db: Session = DBDep,
):
    """
    Log a contact attempt for analytics (Issue #12 - Optional).

    This helps track:
    - Platform engagement
    - Conversion rates
    - Popular users
    - Potential abuse/spam

    Args:
        log_data: Contact log data
        current_user: Authenticated user
        db: Database session

    Returns:
        ContactLogResponse confirming log
    """
    source_user_id = current_user['user_id']

    # Verify target user exists
    target_user = db.query(User).filter(User.id == log_data.target_user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found"
        )

    # Create contact log
    contact_log = ContactLog(
        source_user_id=UUID(source_user_id),
        target_user_id=UUID(log_data.target_user_id),
        contact_method=log_data.contact_method,
        created_at=datetime.utcnow()
    )

    db.add(contact_log)
    db.commit()

    logger.info(
        f"Contact logged: {source_user_id} -> {log_data.target_user_id} "
        f"via {log_data.contact_method}"
    )

    return ContactLogResponse(success=True)
