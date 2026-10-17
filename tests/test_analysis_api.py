import io
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient


def test_analyze_python_project_endpoint(client: TestClient, tmp_path: Path):
    """Test full upload + static analysis pipeline via API."""
    # 1. Create a zip project (Situation B: no manifest, imports external packages)
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("app.py", "import requests\nfrom bs4 import BeautifulSoup\nimport json\n")
        zf.writestr("helper.py", "def greet(): return 'hi'\n")
    zip_bytes.seek(0)

    # 2. Upload archive
    upload_res = client.post(
        "/api/upload",
        files={"file": ("scrape_tool.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201
    session_id = upload_res.json()["session_id"]

    # 3. Request static analysis
    analyze_res = client.post(f"/api/analyze/{session_id}")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    # Verify language detection
    assert data["session_id"] == session_id
    assert data["languages"]["primary_language"] == "Python"
    assert data["summary"]["situation"] == "SITUATION_B"

    # Verify dependency analysis
    py_analysis = data["python_analysis"]
    assert py_analysis is not None
    assert "json" in py_analysis["standard_library_modules"]
    assert "helper" in py_analysis["local_project_modules"]

    ext_names = [d["name"] for d in py_analysis["external_dependencies"]]
    assert "requests" in ext_names
    assert "bs4" in ext_names


def test_analyze_nonexistent_session(client: TestClient):
    """Test analyzing an invalid session ID returns 404."""
    response = client.post("/api/analyze/invalid-session-uuid-1234")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"] == "SessionNotFound"
