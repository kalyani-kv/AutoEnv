from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime, timezone
from pathlib import Path

from .config import STATIC_DIR, MAX_UPLOAD_SIZE_BYTES, MAX_FILE_COUNT, MAX_EXTRACTED_SIZE_BYTES
from .api.upload import router as upload_router

app = FastAPI(
    title="AutoEnv API",
    description="Multi-Language Automatic Dependency Reconstruction & Environment Recovery System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for local developer dashboard communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(upload_router)


@app.get("/api/health", tags=["System"])
async def health_check():
    """System health check and runtime configuration parameters."""
    return {
        "status": "online",
        "service": "AutoEnv",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "security_limits": {
            "max_upload_size_mb": MAX_UPLOAD_SIZE_BYTES // (1024 * 1024),
            "max_extracted_size_mb": MAX_EXTRACTED_SIZE_BYTES // (1024 * 1024),
            "max_file_count": MAX_FILE_COUNT,
        },
    }


# Mount static frontend dashboard if frontend directory exists
index_html = STATIC_DIR / "index.html"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_dashboard():
        if index_html.exists():
            return FileResponse(str(index_html))
        return {
            "message": "AutoEnv backend is running. Frontend UI will be available at this route once index.html is loaded.",
            "docs": "/docs",
        }
