from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..services.workspace import workspace_manager
from ..analyzers.detector import LanguageDetector
from ..analyzers.python_analyzer import PythonAnalyzer
from ..analyzers.base import (
    LanguageDetectionResult,
    DependencyAnalysisResult,
)

router = APIRouter(prefix="/api", tags=["Analysis & Inspection"])


class AnalysisResponse(BaseModel):
    session_id: str
    project_name: str
    languages: LanguageDetectionResult
    python_analysis: Optional[DependencyAnalysisResult] = None
    summary: Dict[str, Any]


@router.post(
    "/analyze/{session_id}",
    response_model=AnalysisResponse,
    summary="Statically analyze project languages and extract dependencies",
)
async def analyze_project(session_id: str):
    session = workspace_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SessionNotFound", "message": f"Session '{session_id}' not found.", "category": "Lookup"},
        )

    project_dir = Path(session.workspace_dir)
    if not project_dir.exists() or not project_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "WorkspaceMissing", "message": "Project workspace directory does not exist.", "category": "Workspace"},
        )

    # 1. Detect all programming languages statically
    detector = LanguageDetector()
    lang_result = detector.detect(project_dir)

    # 2. If Python is detected, perform static AST dependency analysis
    python_analysis: Optional[DependencyAnalysisResult] = None
    has_python = any(l.name == "Python" for l in lang_result.all_detected_languages)

    if has_python:
        py_analyzer = PythonAnalyzer()
        python_analysis = py_analyzer.analyze_dependencies(project_dir)

    # 3. Formulate human-readable summary
    summary: Dict[str, Any] = {
        "primary_language": lang_result.primary_language or "Unknown",
        "total_source_files": lang_result.total_source_files,
        "languages_found": [l.name for l in lang_result.all_detected_languages],
    }

    if python_analysis:
        summary["situation"] = python_analysis.situation.code
        summary["situation_description"] = python_analysis.situation.description
        summary["external_dependencies_count"] = len(python_analysis.external_dependencies)
        summary["stdlib_modules_count"] = len(python_analysis.standard_library_modules)
        summary["local_modules_count"] = len(python_analysis.local_project_modules)
        summary["missing_from_manifest_count"] = len(python_analysis.missing_from_manifest)
        summary["unused_in_manifest_count"] = len(python_analysis.unused_in_manifest)
        summary["syntax_errors_count"] = len(python_analysis.syntax_errors)

    return AnalysisResponse(
        session_id=session.session_id,
        project_name=session.project_name,
        languages=lang_result,
        python_analysis=python_analysis,
        summary=summary,
    )
