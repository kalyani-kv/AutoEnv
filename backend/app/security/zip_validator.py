import os
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, List

from ..config import (
    MAX_UPLOAD_SIZE_BYTES,
    MAX_EXTRACTED_SIZE_BYTES,
    MAX_FILE_COUNT,
    MAX_COMPRESSION_RATIO,
    CHUNK_SIZE_BYTES,
)


class ZipValidationError(Exception):
    """Base exception for all archive validation and security rejections."""
    pass


class ZipSlipError(ZipValidationError):
    """Raised when an archive member attempts directory traversal (ZipSlip vulnerability)."""
    pass


class ZipBombError(ZipValidationError):
    """Raised when archive decompression violates safety limits (size, file count, or ratio)."""
    pass


class CorruptedZipError(ZipValidationError):
    """Raised when archive header or central directory is corrupted."""
    pass


class EmptyZipError(ZipValidationError):
    """Raised when archive contains no files."""
    pass


def sanitize_archive_member_path(member_name: str, target_dir: Path) -> Path:
    """
    Validate that an archive member path strictly resolves inside the target directory.
    
    Protects against ZipSlip directory traversal attacks (e.g. '../../etc/passwd',
    absolute paths '/bin/sh', or Windows drive letters 'C:\\Windows\\evil.bat').
    """
    # Reject drive letters or absolute root paths directly
    if member_name.startswith(("/", "\\")) or (len(member_name) > 1 and member_name[1] == ":"):
        raise ZipSlipError(
            f"Security rejection: Absolute path or drive specifier detected in archive member: '{member_name}'"
        )

    # Normalize target directory to absolute canonical path
    resolved_target = target_dir.resolve()
    
    # Compute the full resolved path of the extracted member
    target_path = (target_dir / member_name).resolve()

    # Enforce that the target_path shares the resolved_target as its common root
    try:
        common = os.path.commonpath([str(resolved_target), str(target_path)])
    except ValueError:
        # Happens on Windows if paths are on different drive letters
        raise ZipSlipError(
            f"Security rejection: Cross-drive path traversal detected in member: '{member_name}'"
        )

    if common != str(resolved_target):
        raise ZipSlipError(
            f"Security rejection: Path traversal attempt detected in archive member: '{member_name}'"
        )

    return target_path


def validate_and_extract_zip(
    zip_path: Path,
    target_dir: Path,
    max_upload_size: int = MAX_UPLOAD_SIZE_BYTES,
    max_extracted_size: int = MAX_EXTRACTED_SIZE_BYTES,
    max_file_count: int = MAX_FILE_COUNT,
    max_compression_ratio: float = MAX_COMPRESSION_RATIO,
) -> Dict[str, Any]:
    """
    Safely validates and extracts a ZIP archive into target_dir.
    
    Guarantees:
    1. Archive file exists and does not exceed max_upload_size.
    2. Archive is a valid zip with non-corrupted central directory.
    3. ZipSlip directory traversal attacks are completely blocked.
    4. Decompression bomb limits (uncompressed size, file count, compression ratio) are enforced.
    5. Clean cleanup of target_dir if any validation fails during streaming.
    """
    if not zip_path.is_file():
        raise CorruptedZipError(f"Archive file not found: {zip_path}")

    file_size = zip_path.stat().st_size
    if file_size > max_upload_size:
        raise ZipBombError(
            f"Archive upload size ({file_size} bytes) exceeds maximum allowed size ({max_upload_size} bytes)."
        )

    if not zipfile.is_zipfile(zip_path):
        raise CorruptedZipError("Uploaded file is not a valid ZIP archive.")

    try:
        zf = zipfile.ZipFile(zip_path, mode="r")
    except Exception as exc:
        raise CorruptedZipError(f"Failed to open ZIP archive: {exc}") from exc

    with zf:
        # Test integrity of ZIP header/CRC
        first_bad_file = zf.testzip()
        if first_bad_file is not None:
            raise CorruptedZipError(f"Corrupted archive member detected: '{first_bad_file}'")

        members = zf.infolist()
        if not members:
            raise EmptyZipError("ZIP archive is empty (contains 0 members).")

        # Filter out root folder entries if any
        non_dir_members = [m for m in members if not m.is_dir() and not m.filename.endswith(("/", "\\"))]
        if not non_dir_members:
            raise EmptyZipError("ZIP archive contains no files.")

        if len(members) > max_file_count:
            raise ZipBombError(
                f"Archive contains {len(members)} entries, exceeding the maximum safe limit of {max_file_count}."
            )

        # Pre-validate all paths to reject ZipSlip before extracting any file
        for member in members:
            sanitize_archive_member_path(member.filename, target_dir)

        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)

        total_uncompressed = 0
        total_compressed = 0
        extracted_file_paths: List[str] = []

        try:
            for member in members:
                dest_path = sanitize_archive_member_path(member.filename, target_dir)

                if member.is_dir() or member.filename.endswith(("/", "\\")):
                    dest_path.mkdir(parents=True, exist_ok=True)
                    continue

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                total_compressed += member.compress_size

                # Stream extraction in chunks to prevent memory spikes
                with zf.open(member, mode="r") as source, open(dest_path, "wb") as dest:
                    while True:
                        chunk = source.read(CHUNK_SIZE_BYTES)
                        if not chunk:
                            break
                        dest.write(chunk)
                        total_uncompressed += len(chunk)

                        if total_uncompressed > max_extracted_size:
                            raise ZipBombError(
                                f"Decompressed size exceeded maximum threshold of {max_extracted_size} bytes."
                            )

                # Compression ratio check for archives that decompress disproportionately
                if total_compressed > 0:
                    current_ratio = total_uncompressed / total_compressed
                    if current_ratio > max_compression_ratio and total_uncompressed > (1024 * 1024):
                        raise ZipBombError(
                            f"Suspicious compression ratio ({current_ratio:.1f}:1) detected. Exceeds limit {max_compression_ratio}:1."
                        )

                relative_file_path = str(dest_path.relative_to(target_dir)).replace("\\", "/")
                extracted_file_paths.append(relative_file_path)

        except Exception:
            # If any failure occurs during extraction, clean up target_dir completely
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            raise

    return {
        "extracted_file_count": len(extracted_file_paths),
        "total_extracted_size_bytes": total_uncompressed,
        "files": extracted_file_paths,
    }
