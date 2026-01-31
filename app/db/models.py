"""
Base database models and utilities.
Includes geospatial column types for PostGIS.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, String, Float
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
import uuid

from app.db.database import Base


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(Base, TimestampMixin):
    """
    User model - base table for all users (parents and tutors).
    Includes geospatial location support.
    """
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Google OAuth
    google_id = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    picture = Column(String, nullable=True)
    
    # Role & Onboarding
    role = Column(String, nullable=True)  # 'parent' or 'tutor', set once
    onboarded = Column(Boolean, default=False, nullable=False)
    
    # Geospatial data (PostGIS)
    # POINT geometry type - stores latitude/longitude
    # SRID 4326 = WGS 84 coordinate system (standard for GPS)
    location = Column(
        Geometry(geometry_type='POINT', srid=4326),
        nullable=True,
        index=True  # Spatial index for fast queries
    )
    
    # Visibility radius in meters (for privacy)
    visibility_radius_meters = Column(Integer, nullable=True, default=5000)  # 5km default
    
    # Soft delete
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class Parent(Base, TimestampMixin):
    """
    Parent-specific profile data.
    Links to User table via user_id.
    """
    __tablename__ = "parents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Parent-specific fields
    children_ages = Column(String, nullable=True)  # JSON string: ["5", "7", "10"]
    curriculum = Column(String, nullable=True)  # e.g., "Classical", "Charlotte Mason"
    religion = Column(String, nullable=True)  # Optional
    
    # Contact
    whatsapp_number = Column(String, nullable=True)
    whatsapp_enabled = Column(Boolean, default=False)
    
    # Coop
    in_coop = Column(Boolean, default=False)
    coop_name = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<Parent(user_id={self.user_id})>"


class Tutor(Base, TimestampMixin):
    """
    Tutor-specific profile data.
    Links to User table via user_id.
    """
    __tablename__ = "tutors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Tutor-specific fields
    subjects = Column(String, nullable=True)  # JSON string: ["Math", "Science"]
    curriculum = Column(String, nullable=True)
    certifications = Column(String, nullable=True)  # JSON string
    availability = Column(String, nullable=True)  # e.g., "Weekday mornings"
    
    # Contact
    whatsapp_number = Column(String, nullable=True)
    whatsapp_enabled = Column(Boolean, default=False)
    
    # Verification
    verification_status = Column(String, default="pending")  # pending, verified, rejected
    verified_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Tutor(user_id={self.user_id}, status={self.verification_status})>"


# Geospatial helper functions
def create_point_from_lat_lng(latitude: float, longitude: float) -> str:
    """
    Create a WKT (Well-Known Text) point string from lat/lng.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
    
    Returns:
        WKT string: 'POINT(longitude latitude)'
    
    Example:
        >>> create_point_from_lat_lng(-1.286389, 36.817223)
        'POINT(36.817223 -1.286389)'
    """
    return f'POINT({longitude} {latitude})'


def distance_meters_query(point1, point2):
    """
    Calculate distance between two geographic points in meters.
    Uses PostGIS ST_Distance with geography cast.
    
    Usage in SQLAlchemy:
        from sqlalchemy import func
        distance = func.ST_Distance(
            func.ST_Transform(User.location, 4326)::Geography,
            func.ST_GeomFromText(point_wkt, 4326)::Geography
        )
    """
    pass  # Implementation in queries
