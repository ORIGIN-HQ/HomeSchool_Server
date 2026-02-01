"""
Map endpoints - viewport-based pin queries (Issue #8).
This is the core product feature.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, cast, String
from geoalchemy2.functions import ST_Distance, ST_MakeEnvelope, ST_Intersects, ST_X, ST_Y, ST_Transform
from geoalchemy2 import Geography
import logging
import json
from uuid import UUID

from app.db import get_db
from app.db.models import User, Parent, Tutor, create_point_from_lat_lng
from app.schemas.map import MapBoundsQuery, MapPinsResponse, MapPin, PinPreview
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/map", tags=["Map"])

CurrentUserDep = Depends(get_current_user)
DBDep = Depends(get_db)


def calculate_distance(db: Session, location1, location2):
    """
    Calculate distance between two PostGIS points in meters.
    Uses GeoAlchemy2 functions properly to avoid serialization issues.
    
    Args:
        db: Database session
        location1: First location (Geometry POINT)
        location2: Second location (Geometry POINT)
    
    Returns:
        Distance in meters (float) or None
    """
    if location1 is None or location2 is None:
        return None
    
    try:
        # Use GeoAlchemy2 ST_Distance with Geography type
        # The key is to use ST_Transform and cast to Geography inline
        distance = db.query(
            ST_Distance(
                ST_Transform(location1, 4326).cast(Geography),
                ST_Transform(location2, 4326).cast(Geography)
            )
        ).scalar()
        
        return float(distance) if distance else None
    except Exception as e:
        logger.error(f"Distance calculation error: {e}")
        return None


@router.get("/pins", response_model=MapPinsResponse)
async def get_map_pins(
    # Viewport bounds (required)
    ne_lat: float = Query(..., ge=-90, le=90, description="Northeast latitude"),
    ne_lng: float = Query(..., ge=-180, le=180, description="Northeast longitude"),
    sw_lat: float = Query(..., ge=-90, le=90, description="Southwest latitude"),
    sw_lng: float = Query(..., ge=-180, le=180, description="Southwest longitude"),
    
    # Filters (optional)
    type: str = Query("all", description="Filter: parent, tutor, or all"),
    curriculum: str = Query(None, description="Filter by curriculum"),
    max_distance_meters: int = Query(None, ge=500, le=100000, description="Max distance from user"),
    min_age: int = Query(None, ge=0, le=18, description="Min child age (parents only)"),
    max_age: int = Query(None, ge=0, le=18, description="Max child age (parents only)"),
    subject: str = Query(None, description="Filter tutors by subject"),
    
    # Dependencies
    current_user: dict = CurrentUserDep,
    db: Session = DBDep,
):
    """
    Get map pins within viewport bounds.
    
    This is the CORE PRODUCT FEATURE - returns users visible on the map.
    
    Performance targets:
    - < 300ms response time
    - Spatial index used for geo queries
    - Excludes current user
    - Respects visibility radius
    
    Args:
        Viewport bounds (ne_lat, ne_lng, sw_lat, sw_lng)
        Filters (type, curriculum, distance, age, subject)
        current_user: Authenticated user
        db: Database session
    
    Returns:
        MapPinsResponse with pins array and metadata
    """
    user_id = current_user['user_id']
    
    logger.info(
        "Map query: user=%s, bounds=(%.6f,%.6f to %.6f,%.6f), type=%s",
        user_id, sw_lat, sw_lng, ne_lat, ne_lng, type
    )
    
    # Get current user's location for distance calculation
    current_user_obj = db.query(User).filter(User.id == user_id).first()
    user_location = current_user_obj.location if current_user_obj else None
    
    # Base query: onboarded users with location, excluding self
    query = db.query(User).filter(
        and_(
            User.id != user_id,  # Exclude self
            User.onboarded == True,  # Only onboarded users
            User.is_active == True,  # Only active users
            User.location.isnot(None)  # Must have location
        )
    )
    
    # Filter by type (parent/tutor/all)
    if type == "parent":
        query = query.filter(User.role == "parent")
    elif type == "tutor":
        query = query.filter(User.role == "tutor")
    # "all" = no filter
    
    # Spatial filter: within viewport bounds
    # Create bounding box using PostGIS ST_MakeEnvelope
    bbox = ST_MakeEnvelope(sw_lng, sw_lat, ne_lng, ne_lat, 4326)
    query = query.filter(ST_Intersects(User.location, bbox))
    
    # Distance filter (if user has location and max_distance specified)
    if user_location and max_distance_meters:
        # Use a subquery to calculate distance and filter
        # This avoids the caching issue with text() in the main query
        distance_subquery = db.query(
            User.id.label('user_id'),
            ST_Distance(
                ST_Transform(user_location, 4326).cast(Geography),
                ST_Transform(User.location, 4326).cast(Geography)
            ).label('distance')
        ).filter(
            and_(
                User.onboarded == True,
                User.is_active == True,
                User.location.isnot(None)
            )
        ).subquery()
        
        # Join with the subquery and filter by distance
        query = query.join(
            distance_subquery,
            User.id == distance_subquery.c.user_id
        ).filter(
            distance_subquery.c.distance <= max_distance_meters
        )
    
    # Curriculum filter
    if curriculum:
        # Need to join with Parent/Tutor tables
        parent_match = db.query(Parent.user_id).filter(
            Parent.curriculum == curriculum
        )
        
        tutor_match = db.query(Tutor.user_id).filter(
            Tutor.curriculum == curriculum
        )
        
        query = query.filter(
            or_(
                User.id.in_(parent_match),
                User.id.in_(tutor_match)
            )
        )
    
    # Subject filter (tutors only)
    if subject:
        tutor_ids = db.query(Tutor.user_id).filter(
            Tutor.subjects.like(f'%"{subject}"%')  # JSON array contains subject
        )
        
        query = query.filter(User.id.in_(tutor_ids))
    
    # Age filter (parents only) - TODO for future iteration
    # This requires parsing JSON children_ages which is complex
    # Skip for MVP
    
    # Execute query (limit to 500 pins for performance)
    users = query.limit(500).all()
    
    logger.info(f"Found {len(users)} pins in viewport")
    
    # Build response pins
    pins = []
    for user in users:
        # Calculate distance if current user has location
        distance = calculate_distance(db, user_location, user.location)
        
        # Extract lat/lng from PostGIS point
        lat = db.query(ST_Y(user.location)).scalar()
        lng = db.query(ST_X(user.location)).scalar()
        
        # Get role-specific data
        subjects = None
        children_count = None
        in_coop = None
        verification_status = None
        curriculum_value = None
        
        if user.role == "parent":
            parent = db.query(Parent).filter(Parent.user_id == user.id).first()
            if parent:
                curriculum_value = parent.curriculum
                in_coop = parent.in_coop
                if parent.children_ages:
                    try:
                        children_count = len(json.loads(parent.children_ages))
                    except:
                        children_count = None
        
        elif user.role == "tutor":
            tutor = db.query(Tutor).filter(Tutor.user_id == user.id).first()
            if tutor:
                curriculum_value = tutor.curriculum
                verification_status = tutor.verification_status
                if tutor.subjects:
                    try:
                        subjects = json.loads(tutor.subjects)
                    except:
                        subjects = None
        
        # Privacy: Use first name only
        first_name = user.name.split()[0] if user.name else "User"
        
        pin = MapPin(
            id=str(user.id),
            type=user.role,
            latitude=lat,
            longitude=lng,
            name=first_name,
            curriculum=curriculum_value,
            distance_meters=distance,
            subjects=subjects,
            children_count=children_count,
            in_coop=in_coop,
            verification_status=verification_status
        )
        pins.append(pin)
    
    # Build filters summary
    filters_applied = {
        "type": type,
        "curriculum": curriculum,
        "max_distance_meters": max_distance_meters,
        "subject": subject
    }
    
    return MapPinsResponse(
        pins=pins,
        total=len(pins),
        filters_applied=filters_applied
    )


@router.get("/preview/{user_id}", response_model=PinPreview)
async def get_pin_preview(
    user_id: UUID,
    current_user: dict = CurrentUserDep,
    db: Session = DBDep,
):
    """
    Get lightweight preview for a map pin.
    
    Called when user clicks a pin on the map.
    Returns minimal data for bottom sheet preview.
    
    Args:
        user_id: Target user ID
        current_user: Authenticated user
        db: Database session
    
    Returns:
        PinPreview with role-specific data
    
    Raises:
        HTTPException 404: User not found or not visible
    """
    requesting_user_id = current_user['user_id']
    
    # Get target user
    user = db.query(User).filter(
        and_(
            User.id == user_id,
            User.onboarded == True,
            User.is_active == True
        )
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or not available"
        )
    
    # Calculate distance (if requesting user has location)
    distance = None
    requesting_user = db.query(User).filter(User.id == requesting_user_id).first()
    if requesting_user and requesting_user.location and user.location:
        distance = calculate_distance(db, requesting_user.location, user.location)
    
    # Build preview based on role
    preview_data = {
        "id": str(user.id),
        "type": user.role,
        "name": user.name,
        "distance_meters": distance
    }
    
    if user.role == "parent":
        parent = db.query(Parent).filter(Parent.user_id == user.id).first()
        if parent:
            preview_data.update({
                "curriculum": parent.curriculum,
                "children_ages": json.loads(parent.children_ages) if parent.children_ages else None,
                "in_coop": parent.in_coop,
                "coop_name": parent.coop_name,
                "whatsapp_enabled": parent.whatsapp_enabled
            })
    
    elif user.role == "tutor":
        tutor = db.query(Tutor).filter(Tutor.user_id == user.id).first()
        if tutor:
            preview_data.update({
                "curriculum": tutor.curriculum,
                "subjects": json.loads(tutor.subjects) if tutor.subjects else None,
                "availability": tutor.availability,
                "whatsapp_enabled": tutor.whatsapp_enabled
            })
    
    return PinPreview(**preview_data)
