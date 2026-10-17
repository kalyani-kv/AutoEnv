"""API routes package."""
from .upload import router as upload_router
from .analysis import router as analysis_router
from .resolve import router as resolve_router

__all__ = ["upload_router", "analysis_router", "resolve_router"]
