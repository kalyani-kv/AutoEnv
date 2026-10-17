from typing import Dict, Optional

# Curated, battle-tested import symbol to PyPI distribution package name mappings.
# In Python, the imported top-level module often differs significantly from the PyPI package.
PYTHON_KNOWN_MAPPINGS: Dict[str, Dict[str, str]] = {
    "cv2": {
        "package": "opencv-python",
        "notes": "OpenCV Python bindings import as 'cv2' but are packaged as 'opencv-python'.",
    },
    "pil": {
        "package": "Pillow",
        "notes": "Pillow is the modern fork of PIL; code uses 'from PIL import Image'.",
    },
    "bs4": {
        "package": "beautifulsoup4",
        "notes": "BeautifulSoup v4 is imported as 'bs4' and distributed as 'beautifulsoup4'.",
    },
    "yaml": {
        "package": "PyYAML",
        "notes": "YAML parser imports as 'yaml' and is packaged as 'PyYAML'.",
    },
    "sklearn": {
        "package": "scikit-learn",
        "notes": "Scikit-Learn machine learning library imports as 'sklearn'.",
    },
    "dateutil": {
        "package": "python-dateutil",
        "notes": "Extensions to the standard Python datetime module packaged as 'python-dateutil'.",
    },
    "dotenv": {
        "package": "python-dotenv",
        "notes": "Reads key-value pairs from .env and sets them as environment variables.",
    },
    "jwt": {
        "package": "PyJWT",
        "notes": "JSON Web Token library for Python packaged as 'PyJWT'.",
    },
    "git": {
        "package": "GitPython",
        "notes": "Git repository interaction library imports as 'git' and is distributed as 'GitPython'.",
    },
    "fitz": {
        "package": "PyMuPDF",
        "notes": "PyMuPDF PDF/document processing library imports as 'fitz'.",
    },
    "openssl": {
        "package": "pyOpenSSL",
        "notes": "Python wrapper around the OpenSSL library.",
    },
    "magic": {
        "package": "python-magic",
        "notes": "File type identification library based on libmagic.",
    },
    "serial": {
        "package": "pyserial",
        "notes": "Serial communication library imports as 'serial'.",
    },
    "psycopg2": {
        "package": "psycopg2-binary",
        "notes": "PostgreSQL adapter for Python (binary wheel recommended for zero compilation).",
    },
    "crypto": {
        "package": "pycryptodome",
        "notes": "Cryptographic library replacing deprecated PyCrypto; imports as 'Crypto'.",
    },
    "docx": {
        "package": "python-docx",
        "notes": "Microsoft Word (.docx) file manipulation library.",
    },
    "pptx": {
        "package": "python-pptx",
        "notes": "PowerPoint (.pptx) file manipulation library.",
    },
    "jose": {
        "package": "python-jose",
        "notes": "JavaScript Object Signing and Encryption (JOSE) implementation for Python.",
    },
    "multipart": {
        "package": "python-multipart",
        "notes": "Streaming multipart parser for Python ASGI/WSGI applications.",
    },
    "socks": {
        "package": "PySocks",
        "notes": "SOCKS proxy client module imports as 'socks'.",
    },
    "websocket": {
        "package": "websocket-client",
        "notes": "WebSocket client for Python imports as 'websocket'.",
    },
    "usb": {
        "package": "pyusb",
        "notes": "USB access library imports as 'usb'.",
    },
    "kafka": {
        "package": "kafka-python",
        "notes": "Apache Kafka client for Python imports as 'kafka'.",
    },
    "opengl": {
        "package": "PyOpenGL",
        "notes": "Standard OpenGL bindings for Python.",
    },
    "wx": {
        "package": "wxPython",
        "notes": "Cross-platform GUI toolkit imports as 'wx'.",
    },
}


def lookup_known_mapping(import_name: str) -> Optional[Dict[str, str]]:
    """Look up an import symbol in the known mapping dictionary (case-insensitive)."""
    return PYTHON_KNOWN_MAPPINGS.get(import_name.lower())
