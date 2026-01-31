"""
Profile endpoints - Parent and Tutor onboarding.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
import uuid
import json

from app.db import get_db
from app.db.models import User, Parent, Tutor, create_point_from_lat_lng
from app.schemas.profiles import (
    ParentProfileCreate, 
    TutorProfileCreate, 
    ProfileResponse
)
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Profiles"])


@router.post("/parents", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_parent_profile(
    profile_data: ParentProfileCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    
    logger.info(f"Parent profile created for user {user_id} at ({profile_data.location.latitude}, {profile_data.location.longitude})")
    
    return ProfileResponse(
        id=str(parent.id),
        user_id=str(parent.user_id),
        created_at=parent.created_at,
        message="Parent profile created successfully. You are now visible on the map!"
    )


@router.post("/tutors", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_tutor_profile(
    profile_data: TutorProfileCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    
    logger.info(f"Tutor profile created for user {user_id} at ({profile_data.location.latitude}, {profile_data.location.longitude})")
    
    return ProfileResponse(
        id=str(tutor.id),
        user_id=str(tutor.user_id),
        created_at=tutor.created_at,
        message="Tutor profile created successfully. You are now visible on the map!"  # ← CHANGED MESSAGE
    )
