"""
Authentication endpoints - Clerk JWT verification.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from app.db import get_db
from app.db.models import User
from app.schemas.auth import UserProfile
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

db_dep = Depends(get_db)
CurrentUserDep = Depends(get_current_user)


class SetRoleRequest(BaseModel):
    """Request body for setting user role."""
    role: str


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: dict = CurrentUserDep,
    db: Session = db_dep,
):
    """
    Get current user profile from Clerk JWT.

    This endpoint allows frontend to:
    - Check if user is authenticated
    - Determine if user needs onboarding (onboarded=False)
    - Get user's role to show appropriate UI
    - Skip directly to map if onboarded=True

    The Clerk JWT is automatically verified by the get_current_user dependency.
    If the user doesn't exist locally, they are automatically created from Clerk data.

    Fast path for returning users:
    1. Frontend gets Clerk session token
    2. Calls GET /auth/me with Authorization: Bearer <token>
    3. If onboarded=True → go to map
    4. If onboarded=False → show onboarding

    Args:
        current_user: Authenticated user from Clerk JWT
        db: Database session

    Returns:
        UserProfile with current user data

    Raises:
        HTTPException 401: Invalid or expired JWT (handled by dependency)
        HTTPException 404: User not found
    """
    user_id = current_user['user_id']

    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        logger.error(f"User {user_id} not found despite valid JWT")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    logger.info(f"User profile retrieved: {user.email} (onboarded={user.onboarded})")

    return UserProfile(
        id=str(user.id),
        email=user.email,
        name=user.name,
        picture=user.picture,
        role=user.role,
        onboarded=user.onboarded
    )


@router.post("/set-role", response_model=UserProfile)
async def set_user_role(
    request: SetRoleRequest,
    current_user: dict = CurrentUserDep,
    db: Session = db_dep,
):
    """
    Set user role (parent or tutor).

    This can only be done once. After the role is set, it cannot be changed.
    This is called during onboarding when the user selects their role.

    Args:
        request: Contains the role to set ('parent' or 'tutor')
        current_user: Authenticated user from Clerk JWT
        db: Database session

    Returns:
        Updated UserProfile

    Raises:
        HTTPException 400: Role already set or invalid role
        HTTPException 404: User not found
    """
    if request.role not in ['parent', 'tutor']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'parent' or 'tutor'"
        )

    user_id = current_user['user_id']
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already set and cannot be changed"
        )

    user.role = request.role
    db.commit()
    db.refresh(user)

    logger.info(f"Role set to '{request.role}' for user {user.email}")

    return UserProfile(
        id=str(user.id),
        email=user.email,
        name=user.name,
        picture=user.picture,
        role=user.role,
        onboarded=user.onboarded
    )
