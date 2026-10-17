import io
import zipfile
from fastapi.testclient import TestClient


def test_resolve_project_api(client: TestClient):
    """
    Test uploading a project with alias imports (cv2, bs4), direct import (fastapi),
    and an unknown package, then verifying resolution API results.
    """
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr(
            "main.py",
            "import cv2\nfrom bs4 import BeautifulSoup\nimport unknown_private_sdk_xyz\nimport os\n",
        )
    zip_bytes.seek(0)

    # 1. Upload
    upload_res = client.post(
        "/api/upload",
        files={"file": ("vision_project.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201
    session_id = upload_res.json()["session_id"]

    # 2. Resolve
    resolve_res = client.post(f"/api/resolve/{session_id}")
    assert resolve_res.status_code == 200
    data = resolve_res.json()

    assert data["session_id"] == session_id
    assert data["total_imports"] == 3  # cv2, bs4, unknown_private_sdk_xyz (os is stdlib)

    resolved_map = {r["import_symbol"]: r for r in data["resolved_dependencies"]}
    unresolved_map = {r["import_symbol"]: r for r in data["unresolved_dependencies"]}

    # cv2 must map to opencv-python via known_mapping
    assert "cv2" in resolved_map
    assert resolved_map["cv2"]["package_name"] == "opencv-python"
    assert resolved_map["cv2"]["confidence"] == "CONFIDENT"
    assert resolved_map["cv2"]["resolution_method"] == "known_mapping"

    # bs4 must map to beautifulsoup4 via known_mapping
    assert "bs4" in resolved_map
    assert resolved_map["bs4"]["package_name"] == "beautifulsoup4"
    assert resolved_map["bs4"]["confidence"] == "CONFIDENT"

    # unknown_private_sdk_xyz must be in unresolved_dependencies
    assert "unknown_private_sdk_xyz" in unresolved_map
    assert unresolved_map["unknown_private_sdk_xyz"]["package_name"] is None
    assert unresolved_map["unknown_private_sdk_xyz"]["confidence"] == "UNRESOLVED"
    assert unresolved_map["unknown_private_sdk_xyz"]["requires_user_approval"] is True


def test_resolve_nonexistent_session(client: TestClient):
    """Test resolving an invalid session ID returns 404."""
    response = client.post("/api/resolve/non-existent-session-uuid-999")
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "SessionNotFound"
