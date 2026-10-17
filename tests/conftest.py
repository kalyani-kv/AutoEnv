import io
import zipfile
import pytest
from pathlib import Path
from typing import Generator
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.workspace import workspace_manager


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def temp_test_dir(tmp_path: Path) -> Path:
    """Provides an isolated directory for test file creation."""
    return tmp_path


@pytest.fixture
def valid_zip_path(tmp_path: Path) -> Path:
    """Creates a legitimate test project ZIP with valid files."""
    zip_file = tmp_path / "valid_project.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("src/main.py", "import os\nprint('Hello AutoEnv')\n")
        zf.writestr("src/utils.py", "def add(a, b):\n    return a + b\n")
        zf.writestr("config/settings.json", '{"env": "development"}')
    return zip_file


@pytest.fixture
def zip_slip_archive(tmp_path: Path) -> Path:
    """Creates a malicious ZIP containing a path traversal (ZipSlip) attempt."""
    zip_file = tmp_path / "malicious_zipslip.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        # Dangerous relative traversal path
        zf.writestr("../../escaped_payload.txt", "MALICIOUS PAYLOAD OUTSIDE WORKSPACE")
        zf.writestr("harmless.txt", "Harmless content")
    return zip_file


@pytest.fixture
def empty_zip_archive(tmp_path: Path) -> Path:
    """Creates a ZIP file with 0 members."""
    zip_file = tmp_path / "empty_project.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        pass
    return zip_file


@pytest.fixture
def corrupted_zip_archive(tmp_path: Path) -> Path:
    """Creates a file with .zip extension but invalid contents."""
    corrupted_file = tmp_path / "corrupted_archive.zip"
    corrupted_file.write_bytes(b"THIS IS NOT A VALID ZIP HEADER ARCHIVE CONTENT 1234567890")
    return corrupted_file
