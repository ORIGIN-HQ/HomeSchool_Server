"""
Map schemas for viewport-based queries and pin responses.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime


class MapBoundsQuery(BaseModel):
    """Query parameters for viewport-based map queries"""
    ne_lat: float = Field(..., ge=-90, le=90, description="Northeast latitude")
    ne_lng: float = Field(..., ge=-180, le=180, description="Northeast longitude")
    sw_lat: float = Field(..., ge=-90, le=90, description="Southwest latitude")
    sw_lng: float = Field(..., ge=-180, le=180, description="Southwest longitude")

    # Filters
    type: Literal["parent", "tutor", "all"] = Field(
        default="all",
        description="Filter by user type"
    )
    curriculum: Optional[str] = Field(None, description="Filter by curriculum")
    max_distance_meters: Optional[int] = Field(
        None,
        ge=500,
        le=100000,
        description="Max distance from user (500m - 100km)"
    )
    min_age: Optional[int] = Field(None, ge=0, le=18, description="Min child age (parents)")
    max_age: Optional[int] = Field(None, ge=0, le=18, description="Max child age (parents)")
    subject: Optional[str] = Field(None, description="Filter tutors by subject")

    @validator('sw_lat')
    def validate_latitude_bounds(cls, v, values):
        """Ensure SW latitude is less than NE latitude"""
        if 'ne_lat' in values and v >= values['ne_lat']:
            raise ValueError('sw_lat must be less than ne_lat')
        return v

    @validator('sw_lng')
    def validate_longitude_bounds(cls, v, values):
        """Ensure proper longitude bounds"""
        # Note: Longitude can wrap around (e.g., -179 to 179)
        # For simplicity, we'll allow any valid range
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "ne_lat": -1.250000,
                "ne_lng": 36.850000,
                "sw_lat": -1.320000,
                "sw_lng": 36.780000,
                "type": "all",
                "curriculum": "Classical"
            }
        }


class MapPin(BaseModel):
    """Individual pin on the map - minimal data for performance"""
    id: str = Field(..., description="User ID")
    type: Literal["parent", "tutor"] = Field(..., description="User type")
    latitude: float
    longitude: float
    name: str = Field(..., description="User's name (first name only for privacy)")
    curriculum: Optional[str] = None
    distance_meters: Optional[float] = Field(None, description="Distance from current user")

    # Optional preview data
    subjects: Optional[list[str]] = Field(None, description="Tutor subjects")
    children_count: Optional[int] = Field(None, description="Number of children (parents)")
    in_coop: Optional[bool] = Field(None, description="Parent in coop")
    verification_status: Optional[str] = Field(None, description="Tutor verification")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "parent",
                "latitude": -1.286389,
                "longitude": 36.817223,
                "name": "Sarah",
                "curriculum": "Classical",
                "distance_meters": 2450.5,
                "children_count": 3,
                "in_coop": True
            }
        }


class MapPinsResponse(BaseModel):
    """Response containing all pins in viewport"""
    pins: list[MapPin]
    total: int = Field(..., description="Total pins returned")
    filters_applied: dict = Field(..., description="Summary of filters used")

    class Config:
        json_schema_extra = {
            "example": {
                "pins": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "type": "parent",
                        "latitude": -1.286389,
                        "longitude": 36.817223,
                        "name": "Sarah",
                        "curriculum": "Classical",
                        "distance_meters": 2450.5,
                        "children_count": 3
                    }
                ],
                "total": 1,
                "filters_applied": {
                    "type": "all",
                    "curriculum": "Classical"
                }
            }
        }


class PinPreview(BaseModel):
    """Lightweight preview when clicking a pin"""
    id: str
    type: Literal["parent", "tutor"]
    name: str
    curriculum: Optional[str] = None
    distance_meters: Optional[float] = None

    # Role-specific preview
    subjects: Optional[list[str]] = None  # Tutor
    availability: Optional[str] = None  # Tutor
    children_ages: Optional[list[str]] = None  # Parent
    in_coop: Optional[bool] = None  # Parent
    coop_name: Optional[str] = None  # Parent

    # Contact status
    whatsapp_enabled: bool = False
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "parent",
                "name": "Sarah Johnson",
                "curriculum": "Classical",
                "distance_meters": 2450.5,
                "children_ages": ["5", "7", "10"],
                "in_coop": True,
                "coop_name": "Nairobi Homeschool Coop",
                "whatsapp_enabled": True
            }
        }
