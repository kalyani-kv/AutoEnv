"""API routes package."""
from .upload import router as upload_router
from .analysis import router as analysis_router

__all__ = ["upload_router", "analysis_router"]
