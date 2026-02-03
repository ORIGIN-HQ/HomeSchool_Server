"""
Clerk JWT verification service.
Verifies tokens issued by Clerk and extracts user information.
ENHANCED: Supports test mode tokens for development/testing.
"""
import logging
import httpx
from jose import jwt, JWTError
from typing import Optional
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Cache for Clerk's JWKS (JSON Web Key Set)
_jwks_cache: Optional[dict] = None


async def get_clerk_jwks() -> dict:
    """
    Fetch Clerk's JWKS (JSON Web Key Set) for token verification.
    The JWKS contains the public keys used to verify JWT signatures.

    Returns:
        dict: JWKS containing public keys
    """
    global _jwks_cache

    if _jwks_cache is not None:
        return _jwks_cache

    # Clerk JWKS endpoint - derived from the issuer
    # Format: https://<your-clerk-frontend-api>/.well-known/jwks.json
    if not settings.clerk_jwt_issuer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk JWT issuer not configured"
        )

    jwks_url = f"{settings.clerk_jwt_issuer}/.well-known/jwks.json"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
            logger.info("Successfully fetched Clerk JWKS")
            return _jwks_cache
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch Clerk JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch authentication keys"
        )


def get_signing_key(jwks: dict, kid: str) -> Optional[dict]:
    """
    Find the signing key in JWKS that matches the key ID (kid) from the token.

    Args:
        jwks: The JWKS containing public keys
        kid: Key ID from the JWT header

    Returns:
        The matching key dict or None
    """
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


async def verify_clerk_token(token: str) -> dict:
    """
    Verify a Clerk JWT token and return the decoded payload.
    
    ENHANCED: Now supports test mode tokens (HS256) for development/testing.
    Test tokens are identified by:
    - Algorithm: HS256 (instead of RS256)
    - Contains 'user_id' field (instead of 'sub')

    Clerk tokens contain:
    - sub: Clerk user ID (e.g., "user_2abc123...")
    - email: User's email (if available in session claims)
    - first_name, last_name: User's name (if available)
    - image_url: Profile picture URL
    - Custom claims from JWT templates

    Test tokens contain:
    - user_id: Local database user UUID
    - email: User's email
    - role: User's role (parent/tutor)

    Args:
        token: The JWT token from the Authorization header

    Returns:
        dict: Decoded token payload with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Check if this is a test mode token (HS256)
        unverified_header = jwt.get_unverified_header(token)
        algorithm = unverified_header.get("alg", "")

        # Test Mode: HS256 tokens
        if algorithm == "HS256":
            logger.info("Test mode: Verifying HS256 token with SECRET_KEY")
            
            try:
                payload = jwt.decode(
                    token,
                    settings.secret_key,
                    algorithms=["HS256"],
                    options={
                        "verify_aud": False,
                        "verify_iss": False,
                        "verify_exp": True,
                    }
                )
                
                # Validate that it has the expected test token structure
                if "user_id" not in payload:
                    logger.warning("Test token missing 'user_id' field")
                    raise credentials_exception
                
                logger.info(f"Test mode: Successfully verified token for user {payload.get('user_id')}")
                return payload
                
            except JWTError as e:
                logger.warning(f"Test token verification failed: {e}")
                raise credentials_exception

        # Production Mode: RS256 Clerk tokens
        kid = unverified_header.get("kid")

        if not kid:
            logger.warning("Token missing key ID (kid)")
            raise credentials_exception

        # Get JWKS and find the signing key
        jwks = await get_clerk_jwks()
        signing_key = get_signing_key(jwks, kid)

        if not signing_key:
            logger.warning(f"No matching key found for kid: {kid}")
            # Clear cache and retry once (key might have rotated)
            global _jwks_cache
            _jwks_cache = None
            jwks = await get_clerk_jwks()
            signing_key = get_signing_key(jwks, kid)

            if not signing_key:
                raise credentials_exception

        # Verify and decode the token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=settings.clerk_jwt_issuer,
            options={
                "verify_aud": False,  # Clerk doesn't always set audience
                "verify_iss": True,
                "verify_exp": True,
            }
        )

        logger.info(f"Successfully verified Clerk token for user: {payload.get('sub')}")
        return payload

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        raise credentials_exception


async def get_clerk_user_info(user_id: str) -> dict:
    """
    Fetch detailed user information from Clerk's Backend API.

    This is useful when you need more user data than what's in the JWT,
    such as email addresses, phone numbers, or metadata.

    Args:
        user_id: Clerk user ID (from token's 'sub' claim)

    Returns:
        dict: User data from Clerk API
    """
    if not settings.clerk_secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk secret key not configured"
        )

    url = f"https://api.clerk.com/v1/users/{user_id}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {settings.clerk_secret_key}",
                    "Content-Type": "application/json",
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch user from Clerk API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user information"
        )


class ClerkAuthService:
    """
    Service class for Clerk authentication operations.
    
    ENHANCED: Now supports test mode for development/testing.
    """

    async def verify_token(self, token: str) -> dict:
        """
        Verify a JWT token (Clerk or test mode).
        
        Automatically detects token type:
        - RS256 with 'kid' header → Clerk token
        - HS256 → Test mode token
        """
        return await verify_clerk_token(token)

    async def get_user_info(self, user_id: str) -> dict:
        """Get detailed user info from Clerk API."""
        return await get_clerk_user_info(user_id)


# Singleton instance
clerk_auth_service = ClerkAuthService()
