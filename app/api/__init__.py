"""API routes"""
from app.api.auth import router as auth_router
from app.api.profiles import router as profiles_router

__all__ = ['auth_router', 'profiles_router']
