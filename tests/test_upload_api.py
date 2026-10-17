from pathlib import Path
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """Test that GET /api/health returns online status and limits."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["service"] == "AutoEnv"
    assert "security_limits" in data
    assert data["security_limits"]["max_upload_size_mb"] == 50


def test_upload_valid_project(client: TestClient, valid_zip_path: Path):
    """Test uploading a legitimate project archive via POST /api/upload."""
    with open(valid_zip_path, "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("valid_project.zip", f, "application/zip")},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["project_name"] == "valid_project"
    assert data["extracted_file_count"] == 3
    assert "session_id" in data
    assert len(data["files"]) == 3
    assert "src/main.py" in data["files"]

    # Test retrieving session details via GET /api/session/{session_id}
    session_res = client.get(f"/api/session/{data['session_id']}")
    assert session_res.status_code == 200
    session_data = session_res.json()
    assert session_data["session_id"] == data["session_id"]
    assert session_data["extracted_file_count"] == 3


def test_upload_zip_slip_attack_returns_422(client: TestClient, zip_slip_archive: Path):
    """Test that an archive containing ZipSlip path traversal returns HTTP 422 with security detail."""
    with open(zip_slip_archive, "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("malicious_zipslip.zip", f, "application/zip")},
        )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["detail"]["error"] == "SecurityViolation"
    assert data["detail"]["category"] == "ZipSlip"


def test_upload_corrupted_file_returns_400(client: TestClient, corrupted_zip_archive: Path):
    """Test that a corrupted archive returns HTTP 400 Bad Request."""
    with open(corrupted_zip_archive, "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("corrupted.zip", f, "application/zip")},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "InvalidArchive"
    assert data["detail"]["category"] == "CorruptedZip"


def test_upload_empty_zip_returns_400(client: TestClient, empty_zip_archive: Path):
    """Test that an empty archive returns HTTP 400 Bad Request."""
    with open(empty_zip_archive, "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("empty.zip", f, "application/zip")},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "EmptyArchive"
    assert data["detail"]["category"] == "EmptyZip"


def test_upload_unsupported_file_extension(client: TestClient, temp_test_dir: Path):
    """Test that uploading a non-zip extension (e.g. .tar or .txt) returns HTTP 400."""
    fake_tar = temp_test_dir / "project.tar"
    fake_tar.write_text("not a zip")

    with open(fake_tar, "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("project.tar", f, "application/x-tar")},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "UnsupportedFileType"
