"""
Contact schemas for WhatsApp integration.
"""
from pydantic import BaseModel, Field
from typing import Optional


class WhatsAppLinkResponse(BaseModel):
    """Response for WhatsApp contact link"""
    whatsapp_url: str = Field(..., description="wa.me deep link")
    phone_number: str = Field(..., description="Formatted phone number")
    prefilled_message: str = Field(..., description="Message to send")
    user_name: str = Field(..., description="Name of contact")
    
    class Config:
        json_schema_extra = {
            "example": {
                "whatsapp_url": "https://wa.me/254712345678?text=Hi%20Sarah%2C%20I%20found%20you%20on%20Homeschool%20Connect...",
                "phone_number": "+254712345678",
                "prefilled_message": "Hi Sarah, I found you on Homeschool Connect and would love to connect!",
                "user_name": "Sarah Johnson"
            }
        }


class ContactLogRequest(BaseModel):
    """Request to log a contact attempt"""
    target_user_id: str
    contact_method: str = Field(default="whatsapp", description="Contact method used")


class ContactLogResponse(BaseModel):
    """Response after logging contact"""
    success: bool
    message: str = "Contact logged successfully"
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Contact logged successfully"
            }
        }
