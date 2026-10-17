from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from ..services.workspace import workspace_manager
from ..analyzers.detector import LanguageDetector
from ..analyzers.python_analyzer import PythonAnalyzer
from ..resolver.python_resolver import PythonDependencyResolver
from ..resolver.base import ResolutionResult

router = APIRouter(prefix="/api", tags=["Package Resolution"])

# In-memory storage of latest session resolution results
_SESSION_RESOLUTIONS = {}


@router.post(
    "/resolve/{session_id}",
    response_model=ResolutionResult,
    summary="Resolve detected import names to external distribution packages (e.g. cv2 -> opencv-python)",
)
async def resolve_project_dependencies(session_id: str):
    session = workspace_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SessionNotFound", "message": f"Session '{session_id}' not found.", "category": "Lookup"},
        )

    project_dir = Path(session.workspace_dir)
    if not project_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "WorkspaceMissing", "message": "Project workspace directory does not exist.", "category": "Workspace"},
        )

    # 1. Analyze dependencies statically via AST
    py_analyzer = PythonAnalyzer()
    analysis_res = py_analyzer.analyze_dependencies(project_dir)

    # 2. Run multi-tier package resolution
    resolver = PythonDependencyResolver()
    resolution_res = resolver.resolve_all(session_id, analysis_res)

    _SESSION_RESOLUTIONS[session_id] = resolution_res
    return resolution_res


@router.get(
    "/resolve/{session_id}",
    response_model=ResolutionResult,
    summary="Get previously computed package resolution results for a session",
)
async def get_resolution_results(session_id: str):
    if session_id not in _SESSION_RESOLUTIONS:
        # Fall back to resolving if not in cache
        return await resolve_project_dependencies(session_id)
    return _SESSION_RESOLUTIONS[session_id]
