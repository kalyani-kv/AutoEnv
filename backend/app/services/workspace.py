import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ..config import WORKSPACE_BASE_DIR


class WorkspaceSession(BaseModel):
    session_id: str
    project_name: str
    workspace_dir: str
    upload_archive_path: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extracted_file_count: int = 0
    total_size_bytes: int = 0
    files: List[str] = Field(default_factory=list)


class WorkspaceManager:
    """
    Manages isolated project sessions.
    
    Structure:
    workspaces/
      └── session_<uuid>/
            ├── uploads/
            │     └── original_project.zip   <-- Untouched original upload
            └── project/                     <-- Extracted project tree
    """

    def __init__(self, base_dir: Path = WORKSPACE_BASE_DIR):
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, WorkspaceSession] = {}

    def create_session(self, original_filename: str) -> WorkspaceSession:
        session_id = str(uuid.uuid4())
        session_root = self.base_dir / f"session_{session_id}"
        uploads_dir = session_root / "uploads"
        project_dir = session_root / "project"

        uploads_dir.mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)

        # Derive clean project name from filename
        safe_name = Path(original_filename).stem or "uploaded_project"
        archive_dest = uploads_dir / f"{safe_name}.zip"

        session = WorkspaceSession(
            session_id=session_id,
            project_name=safe_name,
            workspace_dir=str(project_dir),
            upload_archive_path=str(archive_dest),
        )
        self._sessions[session_id] = session
        return session

    def register_extracted_content(
        self,
        session_id: str,
        file_count: int,
        total_size: int,
        files: List[str],
    ) -> WorkspaceSession:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")

        session.extracted_file_count = file_count
        session.total_size_bytes = total_size
        session.files = sorted(files)
        return session

    def get_session(self, session_id: str) -> Optional[WorkspaceSession]:
        return self._sessions.get(session_id)

    def cleanup_session(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session:
            session_root = Path(session.workspace_dir).parent
            if session_root.exists():
                shutil.rmtree(session_root, ignore_errors=True)
                return True
        return False


# Singleton workspace manager instance for application lifecycle
workspace_manager = WorkspaceManager()
