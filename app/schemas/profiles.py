"""
Profile schemas for parent and tutor onboarding.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime


class LocationData(BaseModel):
    """Location data for user pin"""
    latitude: float = Field(
        ..., ge=-90,
        le=90,
        description="Latitude in decimal degrees"
    )
    longitude: float = Field(
        ..., ge=-180,
        le=180,
        description="Longitude in decimal degrees"
    )
    visibility_radius_meters: Optional[int] = Field(
        5000,
        ge=500,
        le=50000,
        description="Visibility radius in meters (500m - 50km)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": -1.286389,
                "longitude": 36.817223,
                "visibility_radius_meters": 5000
            }
        }


class ParentProfileCreate(BaseModel):
    """Parent profile creation request"""
    # Location
    location: LocationData

    # Parent-specific fields
    children_ages: Optional[list[str]] = Field(None, description="List of children ages")
    curriculum: Optional[str] = Field(None, description="Educational curriculum")
    religion: Optional[str] = None
    whatsapp_number: Optional[str] = None
    whatsapp_enabled: bool = Field(default=False)
    in_coop: bool = Field(default=False)
    coop_name: Optional[str] = None

    @validator('children_ages')
    def validate_children_ages(cls, v):
        if v and len(v) == 0:
            raise ValueError('Children ages cannot be empty list')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "location": {
                    "latitude": -1.286389,
                    "longitude": 36.817223,
                    "visibility_radius_meters": 5000
                },
                "children_ages": ["5", "7", "10"],
                "curriculum": "Classical",
                "religion": "Christian",
                "whatsapp_number": "+254712345678",
                "whatsapp_enabled": True,
                "in_coop": True,
                "coop_name": "Nairobi Homeschool Coop"
            }
        }


class TutorProfileCreate(BaseModel):
    """Tutor profile creation request"""
    # Location (REQUIRED for Issue 5)
    location: LocationData

    # Tutor-specific fields
    subjects: Optional[list[str]] = Field(None, description="Subjects taught")
    curriculum: Optional[str] = None
    certifications: Optional[list[str]] = None
    availability: Optional[str] = None
    whatsapp_number: Optional[str] = None
    whatsapp_enabled: bool = Field(default=False)

    class Config:
        json_schema_extra = {
            "example": {
                "location": {
                    "latitude": -1.286389,
                    "longitude": 36.817223,
                    "visibility_radius_meters": 10000
                },
                "subjects": ["Mathematics", "Science"],
                "curriculum": "British",
                "certifications": ["B.Ed", "TEFL"],
                "availability": "Weekday mornings",
                "whatsapp_number": "+254712345678",
                "whatsapp_enabled": True
            }
        }


class ProfileResponse(BaseModel):
    """Generic profile response"""
    id: str
    user_id: str
    created_at: datetime
    message: str = "Profile created successfully"

    class Config:
        from_attributes = True


class FullParentProfile(BaseModel):
    """Full parent profile response"""
    # User data
    id: str
    name: str
    picture: Optional[str] = None

    # Location data
    latitude: float
    longitude: float
    visibility_radius_meters: int
    distance_meters: Optional[float] = None

    # Parent-specific data
    children_ages: Optional[list[str]] = None
    curriculum: Optional[str] = None
    religion: Optional[str] = None
    in_coop: bool = False
    coop_name: Optional[str] = None

    # Contact (only if enabled)
    whatsapp_number: Optional[str] = None
    whatsapp_enabled: bool = False

    # Metadata
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Sarah Johnson",
                "picture": "https://lh3.googleusercontent.com/...",
                "latitude": -1.286389,
                "longitude": 36.817223,
                "visibility_radius_meters": 5000,
                "distance_meters": 2450.5,
                "children_ages": ["5", "7", "10"],
                "curriculum": "Classical",
                "religion": "Christian",
                "in_coop": True,
                "coop_name": "Nairobi Homeschool Coop",
                "whatsapp_number": "+254712345678",
                "whatsapp_enabled": True,
                "created_at": "2026-01-31T10:30:00"
            }
        }


class FullTutorProfile(BaseModel):
    """Full tutor profile response"""
    # User data
    id: str
    name: str
    picture: Optional[str] = None

    # Location data
    latitude: float
    longitude: float
    visibility_radius_meters: int
    distance_meters: Optional[float] = None

    # Tutor-specific data
    subjects: Optional[list[str]] = None
    curriculum: Optional[str] = None
    certifications: Optional[list[str]] = None
    availability: Optional[str] = None
    verification_status: str = "pending"
    verified_at: Optional[datetime] = None

    # Contact (only if enabled)
    whatsapp_number: Optional[str] = None
    whatsapp_enabled: bool = False

    # Metadata
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "David Kimani",
                "picture": "https://lh3.googleusercontent.com/...",
                "latitude": -1.286389,
                "longitude": 36.817223,
                "visibility_radius_meters": 10000,
                "distance_meters": 3200.0,
                "subjects": ["Mathematics", "Science"],
                "curriculum": "British",
                "certifications": ["B.Ed", "TEFL"],
                "availability": "Weekday mornings",
                "verification_status": "verified",
                "verified_at": "2026-01-31T10:30:00",
                "whatsapp_number": "+254712345678",
                "whatsapp_enabled": True,
                "created_at": "2026-01-31T10:30:00"
            }
        }


class FullProfileResponse(BaseModel):
    """
    Polymorphic response that returns either parent or tutor profile
    based on user role
    """
    type: Literal["parent", "tutor"]
    profile: dict  # Will be FullParentProfile or FullTutorProfile

    class Config:
        json_schema_extra = {
            "example": {
                "type": "parent",
                "profile": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Sarah Johnson",
                    "latitude": -1.286389,
                    "longitude": 36.817223,
                    "children_ages": ["5", "7", "10"],
                    "whatsapp_enabled": True
                }
            }
        }
