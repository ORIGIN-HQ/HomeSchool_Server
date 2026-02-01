"""
Profile endpoints - Parent and Tutor onboarding.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy import and_
from geoalchemy2.functions import ST_X, ST_Y
import logging
from uuid import UUID
import json

from app.db import get_db
from app.db.models import User, Parent, Tutor, create_point_from_lat_lng
from app.schemas.profiles import (
    ParentProfileCreate,
    TutorProfileCreate,
    ProfileResponse
)
from app.core.dependencies import get_current_user
from app.schemas.profiles import FullProfileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Profiles"])

CurrentUserDep = Depends(get_current_user)
DBDep = Depends(get_db)


@router.post(
    "/parents",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_parent_profile(
    profile_data: ParentProfileCreate,
    current_user: dict = CurrentUserDep,
    db: Session = DBDep,
):
    """
    Create parent profile with location.

    This endpoint:
    1. Validates user is authenticated
    2. Checks user role is 'parent'
    3. Saves location to user table (with geo index)
    4. Saves parent-specific data
    5. Marks user as onboarded

    Args:
        profile_data: Parent profile including location
        current_user: Authenticated user from JWT
        db: Database session

    Returns:
        ProfileResponse with confirmation

    Raises:
        HTTPException 400: Invalid role or profile already exists
        HTTPException 404: User not found
    """
    user_id = current_user['user_id']

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify role
    if user.role != 'parent':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User role must be 'parent' to create parent profile"
        )

    # Check if profile already exists
    existing_profile = db.query(Parent).filter(Parent.user_id == user_id).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent profile already exists"
        )

    # Update user location (CRITICAL - Issue 5)
    point_wkt = create_point_from_lat_lng(
        profile_data.location.latitude,
        profile_data.location.longitude
    )
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = profile_data.location.visibility_radius_meters
    user.onboarded = True  # Mark as onboarded

    # Create parent profile
    parent = Parent(
        id=uuid.uuid4(),
        user_id=user_id,
        children_ages=json.dumps(profile_data.children_ages) if profile_data.children_ages else None,
        curriculum=profile_data.curriculum,
        religion=profile_data.religion,
        whatsapp_number=profile_data.whatsapp_number,
        whatsapp_enabled=profile_data.whatsapp_enabled,
        in_coop=profile_data.in_coop,
        coop_name=profile_data.coop_name
    )

    db.add(parent)
    db.commit()
    db.refresh(parent)

    logger.info(
        "Parent profile created for user %s at (%s, %s)",
        user_id,
        profile_data.location.latitude,
        profile_data.location.longitude,
    )

    return ProfileResponse(
        id=str(parent.id),
        user_id=str(parent.user_id),
        created_at=parent.created_at,
        message="Parent profile created successfully. You are now visible on the map!"
    )


@router.post("/tutors", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_tutor_profile(
    profile_data: TutorProfileCreate,
    current_user: dict = CurrentUserDep,
    db: Session = DBDep,
):
    """
    Create tutor profile with location.

    This endpoint:
    1. Validates user is authenticated
    2. Checks user role is 'tutor'
    3. Saves location to user table (with geo index)
    4. Saves tutor-specific data
    5. Marks user as onboarded
    6. Sets verification_status to 'verified' (MVP - auto-verify)  # ← CHANGED

    Args:
        profile_data: Tutor profile including location
        current_user: Authenticated user from JWT
        db: Database session

    Returns:
        ProfileResponse with confirmation

    Raises:
        HTTPException 400: Invalid role or profile already exists
        HTTPException 404: User not found
    """
    user_id = current_user['user_id']

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify role
    if user.role != 'tutor':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User role must be 'tutor' to create tutor profile"
        )

    # Check if profile already exists
    existing_profile = db.query(Tutor).filter(Tutor.user_id == user_id).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tutor profile already exists"
        )

    # Update user location (CRITICAL - Issue 5)
    point_wkt = create_point_from_lat_lng(
        profile_data.location.latitude,
        profile_data.location.longitude
    )
    user.location = func.ST_GeomFromText(point_wkt, 4326)
    user.visibility_radius_meters = profile_data.location.visibility_radius_meters
    user.onboarded = True  # Mark as onboarded

    # Create tutor profile
    tutor = Tutor(
        id=uuid.uuid4(),
        user_id=user_id,
        subjects=json.dumps(profile_data.subjects) if profile_data.subjects else None,
        curriculum=profile_data.curriculum,
        certifications=json.dumps(profile_data.certifications) if profile_data.certifications else None,
        availability=profile_data.availability,
        whatsapp_number=profile_data.whatsapp_number,
        whatsapp_enabled=profile_data.whatsapp_enabled,
        verification_status='verified',  # Auto-verify
        verified_at=func.now()  # Set verification timestamp
    )

    db.add(tutor)
    db.commit()
    db.refresh(tutor)

    logger.info(
        "Tutor profile created for user %s at (%s, %s)",
        user_id,
        profile_data.location.latitude,
        profile_data.location.longitude,
    )

    return ProfileResponse(
        id=str(tutor.id),
        user_id=str(tutor.user_id),
        created_at=tutor.created_at,
        message="Tutor profile created successfully. You are now visible on the map!"  # ← CHANGED MESSAGE
    )


@router.get("/profiles/{user_id}", response_model=FullProfileResponse)
async def get_full_profile(
    user_id: UUID,
    current_user: dict = CurrentUserDep,
    db: Session = DBDep,
):
    """
    Get full profile data for a selected user (Issue #10).
    
    This endpoint returns comprehensive profile information including:
    - User's full name and photo
    - Exact location (lat/lng) - they've already consented by being on the map
    - Role-specific data (parent or tutor details)
    - WhatsApp contact (ONLY if user has enabled it)
    - Distance from requesting user
    
    Privacy considerations:
    - WhatsApp number only returned if whatsapp_enabled=True
    - Only returns data for onboarded, active users
    - Cannot view your own profile (use /auth/me instead)
    
    Args:
        user_id: Target user ID to fetch profile for
        current_user: Authenticated user making the request
        db: Database session
    
    Returns:
        FullProfileResponse with role-specific profile data
    
    Raises:
        HTTPException 404: User not found or not available
        HTTPException 400: Attempting to view own profile
    """
    requesting_user_id = current_user['user_id']
    
    # Prevent viewing own profile
    if str(user_id) == requesting_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot view your own profile. Use GET /auth/me instead."
        )
    
    # Get target user (must be onboarded and active)
    user = db.query(User).filter(
        and_(
            User.id == user_id,
            User.onboarded == True,
            User.is_active == True,
            User.location.isnot(None)
        )
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or profile not available"
        )
    
    logger.info(
        f"User {requesting_user_id} viewing profile of {user_id} (role: {user.role})"
    )
    
    # Calculate distance (if requesting user has location)
    distance = None
    requesting_user = db.query(User).filter(User.id == requesting_user_id).first()
    if requesting_user and requesting_user.location and user.location:
        # Import here to avoid circular imports
        from app.api.map import calculate_distance
        distance = calculate_distance(db, requesting_user.location, user.location)
    
    # Extract lat/lng from PostGIS point
    lat = db.query(ST_Y(user.location)).scalar()
    lng = db.query(ST_X(user.location)).scalar()
    
    # Build role-specific profile
    if user.role == "parent":
        parent = db.query(Parent).filter(Parent.user_id == user.id).first()
        
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent profile not found"
            )
        
        # Parse JSON fields
        children_ages = None
        if parent.children_ages:
            try:
                children_ages = json.loads(parent.children_ages)
            except:
                children_ages = None
        
        # Build response - WhatsApp only if enabled
        profile_data = {
            "id": str(user.id),
            "name": user.name,
            "picture": user.picture,
            "latitude": lat,
            "longitude": lng,
            "visibility_radius_meters": user.visibility_radius_meters,
            "distance_meters": distance,
            "children_ages": children_ages,
            "curriculum": parent.curriculum,
            "religion": parent.religion,
            "in_coop": parent.in_coop,
            "coop_name": parent.coop_name if parent.in_coop else None,
            "whatsapp_number": parent.whatsapp_number if parent.whatsapp_enabled else None,
            "whatsapp_enabled": parent.whatsapp_enabled,
            "created_at": parent.created_at
        }
        
        return FullProfileResponse(
            type="parent",
            profile=profile_data
        )
    
    elif user.role == "tutor":
        tutor = db.query(Tutor).filter(Tutor.user_id == user.id).first()
        
        if not tutor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tutor profile not found"
            )
        
        # Parse JSON fields
        subjects = None
        certifications = None
        
        if tutor.subjects:
            try:
                subjects = json.loads(tutor.subjects)
            except:
                subjects = None
        
        if tutor.certifications:
            try:
                certifications = json.loads(tutor.certifications)
            except:
                certifications = None
        
        # Build response - WhatsApp only if enabled
        profile_data = {
            "id": str(user.id),
            "name": user.name,
            "picture": user.picture,
            "latitude": lat,
            "longitude": lng,
            "visibility_radius_meters": user.visibility_radius_meters,
            "distance_meters": distance,
            "subjects": subjects,
            "curriculum": tutor.curriculum,
            "certifications": certifications,
            "availability": tutor.availability,
            "verification_status": tutor.verification_status,
            "verified_at": tutor.verified_at,
            "whatsapp_number": tutor.whatsapp_number if tutor.whatsapp_enabled else None,
            "whatsapp_enabled": tutor.whatsapp_enabled,
            "created_at": tutor.created_at
        }
        
        return FullProfileResponse(
            type="tutor",
            profile=profile_data
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user role"
        )
