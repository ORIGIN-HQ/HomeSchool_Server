"""
FastAPI dependencies for authentication and authorization.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import verify_token

security = HTTPBearer()
credentials_dep = Depends(security)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = credentials_dep,
) -> dict:
    """
    Dependency to get current authenticated user from JWT.

    Usage:
        @app.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            user_id = current_user['user_id']
            ...

    Returns:
        Dictionary with user_id, email, and role

    Raises:
        HTTPException 401: If token is invalid or missing
    """
    token = credentials.credentials
    payload = verify_token(token)

    # Ensure required fields are present
    if 'user_id' not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    return payload
