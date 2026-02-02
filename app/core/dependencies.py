"""
FastAPI dependencies for authentication and authorization.
Uses Clerk for JWT verification with automatic user sync.
"""
import logging
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.services.clerk_auth import clerk_auth_service
from app.db import get_db
from app.db.models import User

logger = logging.getLogger(__name__)

security = HTTPBearer()
credentials_dep = Depends(security)
db_dep = Depends(get_db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = credentials_dep,
    db: Session = db_dep,
) -> dict:
    """
    Dependency to get current authenticated user from Clerk JWT.

    This dependency:
    1. Verifies the Clerk JWT token
    2. Extracts user info from token + Clerk API
    3. Creates or updates user in local database (auto-sync)
    4. Returns user data for route handlers

    Usage:
        @app.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            user_id = current_user['user_id']
            ...

    Returns:
        Dictionary with user_id, email, role, clerk_id, and onboarded status

    Raises:
        HTTPException 401: If token is invalid or missing
    """
    token = credentials.credentials

    # Verify Clerk JWT
    payload = await clerk_auth_service.verify_token(token)

    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID"
        )

    # Check if user exists in our database (by clerk_id stored in google_id field)
    user = db.query(User).filter(User.google_id == clerk_user_id).first()

    if not user:
        # User doesn't exist locally - fetch from Clerk and create
        logger.info(f"New user detected, syncing from Clerk: {clerk_user_id}")
        user = await sync_user_from_clerk(clerk_user_id, db)

    # Return user data for route handlers
    return {
        "user_id": str(user.id),
        "clerk_id": clerk_user_id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "onboarded": user.onboarded,
    }


async def sync_user_from_clerk(clerk_user_id: str, db: Session) -> User:
    """
    Sync user data from Clerk to local database.

    Called when:
    - User signs in for the first time (auto-registration)
    - User data needs to be refreshed

    Args:
        clerk_user_id: Clerk user ID (e.g., "user_2abc123...")
        db: Database session

    Returns:
        User: The created or updated user record
    """
    # Fetch full user data from Clerk API
    clerk_user = await clerk_auth_service.get_user_info(clerk_user_id)

    # Extract email (Clerk stores emails in an array)
    email_addresses = clerk_user.get("email_addresses", [])
    primary_email_id = clerk_user.get("primary_email_address_id")

    email = None
    for email_obj in email_addresses:
        if email_obj.get("id") == primary_email_id:
            email = email_obj.get("email_address")
            break

    if not email and email_addresses:
        email = email_addresses[0].get("email_address")

    if not email:
        logger.error(f"No email found for Clerk user: {clerk_user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email not available"
        )

    # Build name from Clerk data
    first_name = clerk_user.get("first_name", "")
    last_name = clerk_user.get("last_name", "")
    name = f"{first_name} {last_name}".strip() or email.split("@")[0]

    # Get profile image
    picture = clerk_user.get("image_url")

    # Get metadata (role, onboarded status)
    public_metadata = clerk_user.get("public_metadata", {})
    role = public_metadata.get("role")
    onboarded = public_metadata.get("onboarded", False)

    # Check if user already exists by email (migration case)
    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user:
        # Update existing user with Clerk ID
        logger.info(f"Linking existing user {email} to Clerk ID {clerk_user_id}")
        existing_user.google_id = clerk_user_id  # Store Clerk ID in google_id field
        existing_user.name = name
        existing_user.picture = picture
        if role and not existing_user.role:
            existing_user.role = role
        db.commit()
        db.refresh(existing_user)
        return existing_user

    # Create new user
    logger.info(f"Creating new user: {email}")
    new_user = User(
        id=uuid.uuid4(),
        google_id=clerk_user_id,  # Store Clerk ID in google_id field for now
        email=email,
        name=name,
        picture=picture,
        role=role,
        onboarded=onboarded,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user created with ID: {new_user.id}")
    return new_user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    db: Session = db_dep,
) -> dict | None:
    """
    Optional authentication dependency.

    Returns user data if authenticated, None otherwise.
    Useful for routes that work with or without authentication.

    Usage:
        @app.get("/public-or-private")
        async def route(current_user: dict | None = Depends(get_current_user_optional)):
            if current_user:
                # Authenticated behavior
            else:
                # Public behavior
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
