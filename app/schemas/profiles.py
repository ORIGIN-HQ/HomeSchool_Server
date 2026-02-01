"""
Profile schemas for parent and tutor onboarding.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
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
    # Location (REQUIRED for Issue 5)
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
