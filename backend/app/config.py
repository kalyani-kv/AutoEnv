from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_BASE_DIR = PROJECT_ROOT / "workspaces"
STATIC_DIR = PROJECT_ROOT / "frontend"

# Security & Upload Thresholds
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024        # 50 MB max zip upload
MAX_EXTRACTED_SIZE_BYTES = 200 * 1024 * 1024    # 200 MB max uncompressed content
MAX_FILE_COUNT = 2500                           # Max files inside archive (ZipBomb protection)
MAX_COMPRESSION_RATIO = 100.0                   # Max decompression expansion ratio
CHUNK_SIZE_BYTES = 64 * 1024                    # 64 KB streaming buffer

ALLOWED_ARCHIVE_EXTENSIONS = {".zip"}

# Common build/generated directories to ignore during project analysis
IGNORED_DIRECTORIES = {
    ".git",
    "__pycache__",
    "node_modules",
    "target",
    "bin",
    "obj",
    "vendor",
    "dist",
    "build",
    ".venv",
    "venv",
    ".idea",
    ".vscode"
}
