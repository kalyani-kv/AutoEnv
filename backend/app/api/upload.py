from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from ..config import MAX_UPLOAD_SIZE_BYTES, ALLOWED_ARCHIVE_EXTENSIONS, CHUNK_SIZE_BYTES
from ..services.workspace import workspace_manager, WorkspaceSession
from ..security.zip_validator import (
    validate_and_extract_zip,
    ZipSlipError,
    ZipBombError,
    CorruptedZipError,
    EmptyZipError,
    ZipValidationError,
)

router = APIRouter(prefix="/api", tags=["Upload & Ingestion"])


class UploadResponse(BaseModel):
    status: str
    session_id: str
    project_name: str
    extracted_file_count: int
    total_size_bytes: int
    files: List[str]
    message: str


class ErrorDetail(BaseModel):
    error: str
    message: str
    category: str


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Safely upload, validate, and extract a project ZIP archive",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid or corrupted archive"},
        422: {"model": ErrorDetail, "description": "Security violation (ZipSlip or ZipBomb)"},
    },
)
async def upload_project(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "MissingFilename", "message": "No filename provided in upload.", "category": "InputValidation"},
        )

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_ARCHIVE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "UnsupportedFileType",
                "message": f"Unsupported file extension '{file_ext}'. AutoEnv currently accepts {list(ALLOWED_ARCHIVE_EXTENSIONS)} archives.",
                "category": "FileValidation",
            },
        )

    # 1. Create isolated session directories
    session = workspace_manager.create_session(file.filename)
    archive_dest = Path(session.upload_archive_path)
    workspace_dir = Path(session.workspace_dir)

    # 2. Stream uploaded bytes to disk while enforcing upload size limit
    total_bytes_written = 0
    try:
        with open(archive_dest, "wb") as buffer:
            while True:
                chunk = await file.read(CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                total_bytes_written += len(chunk)
                if total_bytes_written > MAX_UPLOAD_SIZE_BYTES:
                    buffer.close()
                    workspace_manager.cleanup_session(session.session_id)
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail={
                            "error": "ResourceExhaustion",
                            "message": f"Archive upload size exceeds the maximum limit of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
                            "category": "ZipBomb",
                        },
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        workspace_manager.cleanup_session(session.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "UploadSaveError", "message": f"Failed to save upload: {exc}", "category": "Internal"},
        ) from exc

    # 3. Perform security validation and safe extraction
    try:
        extraction_meta = validate_and_extract_zip(archive_dest, workspace_dir)
    except ZipSlipError as exc:
        workspace_manager.cleanup_session(session.session_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"error": "SecurityViolation", "message": str(exc), "category": "ZipSlip"},
        ) from exc
    except ZipBombError as exc:
        workspace_manager.cleanup_session(session.session_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"error": "ResourceExhaustion", "message": str(exc), "category": "ZipBomb"},
        ) from exc
    except EmptyZipError as exc:
        workspace_manager.cleanup_session(session.session_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "EmptyArchive", "message": str(exc), "category": "EmptyZip"},
        ) from exc
    except (CorruptedZipError, ZipValidationError) as exc:
        workspace_manager.cleanup_session(session.session_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "InvalidArchive", "message": str(exc), "category": "CorruptedZip"},
        ) from exc

    # 4. Register extracted files with the session
    workspace_manager.register_extracted_content(
        session_id=session.session_id,
        file_count=extraction_meta["extracted_file_count"],
        total_size=extraction_meta["total_extracted_size_bytes"],
        files=extraction_meta["files"],
    )

    return UploadResponse(
        status="success",
        session_id=session.session_id,
        project_name=session.project_name,
        extracted_file_count=extraction_meta["extracted_file_count"],
        total_size_bytes=extraction_meta["total_extracted_size_bytes"],
        files=extraction_meta["files"],
        message="Project archive validated and extracted safely into isolated workspace.",
    )


@router.get(
    "/session/{session_id}",
    response_model=WorkspaceSession,
    summary="Get session workspace details",
)
async def get_session_details(session_id: str):
    session = workspace_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NotFound", "message": f"Session '{session_id}' not found.", "category": "Lookup"},
        )
    return session
