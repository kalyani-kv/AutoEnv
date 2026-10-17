import zipfile
import pytest
from pathlib import Path

from backend.app.security.zip_validator import (
    validate_and_extract_zip,
    ZipSlipError,
    ZipBombError,
    CorruptedZipError,
    EmptyZipError,
)


def test_valid_zip_extraction(valid_zip_path: Path, temp_test_dir: Path):
    """Test that a legitimate zip extracts completely and safely."""
    target_dir = temp_test_dir / "extracted_valid"
    result = validate_and_extract_zip(valid_zip_path, target_dir)

    assert result["extracted_file_count"] == 3
    assert result["total_extracted_size_bytes"] > 0
    assert "src/main.py" in result["files"]
    assert "src/utils.py" in result["files"]
    assert "config/settings.json" in result["files"]

    # Verify files physically exist on disk
    assert (target_dir / "src" / "main.py").is_file()
    assert (target_dir / "src" / "utils.py").is_file()
    assert (target_dir / "config" / "settings.json").is_file()


def test_zip_slip_rejection(zip_slip_archive: Path, temp_test_dir: Path):
    """
    Test that an archive containing directory traversal (ZipSlip) is blocked.
    Crucially: no files must be written outside the target directory.
    """
    target_dir = temp_test_dir / "extracted_slip"
    escaped_canary = temp_test_dir / "escaped_payload.txt"

    with pytest.raises(ZipSlipError) as exc_info:
        validate_and_extract_zip(zip_slip_archive, target_dir)

    assert "Path traversal attempt detected" in str(exc_info.value)
    # Canary file outside target_dir must NOT exist
    assert not escaped_canary.exists()


def test_zip_slip_absolute_path(temp_test_dir: Path):
    """Test that member with absolute path is rejected immediately."""
    zip_path = temp_test_dir / "absolute_path.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("/root/malicious.sh", "echo evil")

    target_dir = temp_test_dir / "extracted_abs"
    with pytest.raises(ZipSlipError):
        validate_and_extract_zip(zip_path, target_dir)


def test_empty_zip_rejection(empty_zip_archive: Path, temp_test_dir: Path):
    """Test that a zip with zero entries is rejected."""
    target_dir = temp_test_dir / "extracted_empty"
    with pytest.raises(EmptyZipError) as exc_info:
        validate_and_extract_zip(empty_zip_archive, target_dir)

    assert "empty" in str(exc_info.value).lower()


def test_corrupted_zip_rejection(corrupted_zip_archive: Path, temp_test_dir: Path):
    """Test that a non-zip file masquerading as a zip is rejected."""
    target_dir = temp_test_dir / "extracted_corrupted"
    with pytest.raises(CorruptedZipError):
        validate_and_extract_zip(corrupted_zip_archive, target_dir)


def test_file_count_limit_rejection(temp_test_dir: Path):
    """Test that ZipBomb with too many files is stopped by max_file_count threshold."""
    zip_path = temp_test_dir / "too_many_files.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for i in range(15):
            zf.writestr(f"file_{i}.txt", f"content {i}")

    target_dir = temp_test_dir / "extracted_count"
    # Set limit to 10 files
    with pytest.raises(ZipBombError) as exc_info:
        validate_and_extract_zip(zip_path, target_dir, max_file_count=10)

    assert "exceeding the maximum safe limit" in str(exc_info.value)


def test_extracted_size_limit_rejection(temp_test_dir: Path):
    """Test that ZipBomb exceeding max uncompressed size is halted during streaming."""
    zip_path = temp_test_dir / "oversized.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 50 KB of repeating data
        zf.writestr("large.txt", "A" * (50 * 1024))

    target_dir = temp_test_dir / "extracted_size"
    # Restrict uncompressed size to 20 KB
    with pytest.raises(ZipBombError) as exc_info:
        validate_and_extract_zip(zip_path, target_dir, max_extracted_size=20 * 1024)

    assert "Decompressed size exceeded maximum threshold" in str(exc_info.value)
    # Ensure cleanup removed partial extracted files
    assert not target_dir.exists()
