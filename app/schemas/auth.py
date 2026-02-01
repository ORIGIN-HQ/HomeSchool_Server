"""
Authentication schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional


class GoogleAuthRequest(BaseModel):
    """Request body for Google OAuth login"""
    id_token: str = Field(..., description="Google ID token from OAuth flow")
    role: Optional[str] = Field(
        None,
        description="User role: 'parent' or 'tutor' (set once)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "role": "parent"
            }
        }


class AuthResponse(BaseModel):
    """Response for successful authentication"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: "UserProfile"

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "name": "John Doe",
                    "role": "parent",
                    "onboarded": False
                }
            }
        }


class UserProfile(BaseModel):
    """User profile data returned in auth response"""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: Optional[str] = None
    onboarded: bool

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """Data stored in JWT token"""
    user_id: str
    email: str
    role: Optional[str] = None


# Update forward references
AuthResponse.model_rebuild()
