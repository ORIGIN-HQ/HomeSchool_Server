"""
Authentication endpoints - Google OAuth and JWT issuance.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
import uuid

from app.db import get_db
from app.db.models import User
from app.schemas.auth import GoogleAuthRequest, AuthResponse, UserProfile
from app.services.google_auth import google_auth_service
from app.core.security import create_access_token
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

db_dep = Depends(get_db)
CurrentUserDep = Depends(get_current_user)


@router.post("/google", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def google_auth(
    auth_request: GoogleAuthRequest,
    db: Session = db_dep,
):
    """
    Google OAuth authentication endpoint.

    Workflow:
    1. Verify Google ID token
    2. Create new user OR fetch existing user
    3. Optionally set role (only allowed once)
    4. Generate and return JWT

    Args:
        auth_request: Contains Google ID token and optional role
        db: Database session

    Returns:
        AuthResponse with JWT and user profile

    Raises:
        HTTPException 401: Invalid Google token
        HTTPException 400: Role already set or invalid role
    """
    # Verify Google token
    logger.info("Verifying Google token...")
    google_user_info = await google_auth_service.verify_google_token(
        auth_request.id_token
    )

    # Check if user exists
    user = db.query(User).filter(User.google_id == google_user_info['google_id']).first()

    if user:
        logger.info(f"Existing user found: {user.email}")

        # Handle role setting for existing users
        if auth_request.role:
            # Check if role is already set
            if user.role:
                logger.warning(
                    f"User {user.email} attempted to change role from {user.role} to {auth_request.role}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role already set and cannot be changed"
                )

            # Validate role
            if auth_request.role not in ['parent', 'tutor']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role must be 'parent' or 'tutor'"
                )

            # Set role (first time only)
            user.role = auth_request.role
            db.commit()
            db.refresh(user)
            logger.info(f"Role set to '{auth_request.role}' for user {user.email}")

    else:
        # Create new user
        logger.info(f"Creating new user: {google_user_info['email']}")

        # Validate role if provided
        role = None
        if auth_request.role:
            if auth_request.role not in ['parent', 'tutor']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role must be 'parent' or 'tutor'"
                )
            role = auth_request.role

        user = User(
            id=uuid.uuid4(),
            google_id=google_user_info['google_id'],
            email=google_user_info['email'],
            name=google_user_info['name'],
            picture=google_user_info['picture'],
            role=role,
            onboarded=False,  # New users always start not onboarded
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New user created with ID: {user.id}")

    # Generate JWT
    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role
    }
    access_token = create_access_token(data=token_data)

    # Return response
    user_profile = UserProfile(
        id=str(user.id),
        email=user.email,
        name=user.name,
        picture=user.picture,
        role=user.role,
        onboarded=user.onboarded
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_profile
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: dict = CurrentUserDep,
    db: Session = db_dep,
):
    """
    Get current user profile from JWT (Issue #13).

    This endpoint allows frontend to:
    - Check if user is authenticated
    - Determine if user needs onboarding (onboarded=False)
    - Get user's role to show appropriate UI
    - Skip directly to map if onboarded=True

    Fast path for returning users:
    1. Frontend reads JWT from storage
    2. Calls GET /auth/me
    3. If onboarded=True → go to map
    4. If onboarded=False → show onboarding

    Args:
        current_user: Authenticated user from JWT
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
