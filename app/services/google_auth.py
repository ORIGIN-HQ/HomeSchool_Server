"""
Google OAuth token verification service.
"""
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException, status
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleAuthService:
    """Service for verifying Google OAuth tokens"""
    
    def __init__(self):
        self.google_client_id = settings.google_client_id
    
    async def verify_google_token(self, token: str) -> dict:
        """
        Verify Google ID token and extract user information.
        
        Args:
            token: Google ID token from OAuth flow
            
        Returns:
            Dictionary containing user info from Google:
            {
                'google_id': str,
                'email': str,
                'name': str,
                'picture': str
            }
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                self.google_client_id
            )
            
            # Token is valid, extract user info
            google_id = idinfo['sub']
            email = idinfo['email']
            name = idinfo.get('name', '')
            picture = idinfo.get('picture', '')
            
            logger.info(f"Successfully verified Google token for user: {email}")
            
            return {
                'google_id': google_id,
                'email': email,
                'name': name,
                'picture': picture
            }
            
        except ValueError as e:
            # Token verification failed
            logger.error(f"Google token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
        except Exception as e:
            logger.error(f"Unexpected error during Google token verification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )


# Singleton instance
google_auth_service = GoogleAuthService()
