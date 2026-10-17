# AutoEnv — Multi-Language Automatic Dependency Reconstruction & Environment Recovery System

> **A developer receives an unfamiliar software project without documentation, setup instructions, or a dependency manifest. AutoEnv analyzes the project structure, reconstructs external dependencies across multiple programming ecosystems, attempts safe environment setup, verifies configuration, and automatically rolls back failed changes.**

---

## 🛡️ Security Architecture & Trust Boundaries

AutoEnv treats all uploaded archives and unfamiliar code as **untrusted input**. Without kernel-level sandboxing or Docker, safe arbitrary code execution cannot be guaranteed on the host. Therefore, AutoEnv strictly implements a **3-tier boundary architecture**:

1. **Package / Environment Isolation**:
   - Uses dedicated, project-isolated environments (e.g. `venv`, project-local `node_modules`).
   - *Security Note*: Environment isolation prevents host package pollution, but is **not** an OS security sandbox.
2. **Process & Resource Controls**:
   - Subprocess timeouts on CLI runners (`pip`, `py_compile`).
   - Working directory confinement strictly pinned to temporary session folders (`workspaces/session_<uuid>/`).
   - Truncated log buffers to avoid memory exhaustion attacks.
3. **Safe Verification Policy**:
   - **AutoEnv NEVER executes arbitrary application code** (e.g. `python main.py` or entry points).
   - Verification is conducted purely through **static AST parsing**, non-executing syntax compilation (`py_compile`), and disk-level package existence validation.

---

## 🚀 Key Features (Phase 1: Active)

- **Strict Path Traversal Protection (ZipSlip)**: Pre-extraction validation rejecting relative path escapes (`../`), cross-drive letters, and absolute paths using canonical path matching (`os.path.commonpath`).
- **Decompression Bomb Protection (ZipBomb)**:
  - Max upload archive size: **50 MB**
  - Max uncompressed content limit: **200 MB**
  - Max archive file count: **2,500 entries**
  - Streaming decompression ratio circuit breaker (100:1 max ratio).
- **Atomic Workspace Sandboxing**: Every project is extracted into an isolated UUID-scoped temporary session directory (`workspaces/session_<uuid>/`). The original uploaded ZIP is preserved read-only in `uploads/` and is never modified.
- **RESTful API**: Built with FastAPI, Pydantic v2 schemas, and interactive Swagger documentation at `/docs`.
- **Developer Dashboard**: Clean, responsive Single Page Application (SPA) with drag-and-drop ZIP upload and real-time validation feedback.

---

## 📂 Project Structure

```text
AutoEnv/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application & dashboard routing
│   │   ├── config.py                   # Central limits and security thresholds
│   │   ├── api/
│   │   │   └── upload.py               # POST /api/upload & session endpoints
│   │   ├── security/
│   │   │   └── zip_validator.py        # ZipSlip & ZipBomb defensive validator
│   │   └── services/
│   │       └── workspace.py            # Session workspace manager
│   └── requirements.txt
├── frontend/
│   ├── index.html                      # Developer dashboard
│   ├── css/styles.css                  # Modern dark-mode UI
│   └── js/app.js                       # Drag-and-drop & API communication
├── tests/
│   ├── conftest.py                     # Pytest fixtures (legitimate & attack archives)
│   ├── test_zip_validation.py          # Security unit tests (ZipSlip, ZipBomb, Corrupted)
│   └── test_upload_api.py              # API upload integration tests
├── .gitignore
└── README.md
```

---

## 🧪 Automated Testing

Phase 1 includes 13 automated unit and integration tests covering legitimate extraction and security attack vectors:

```bash
# Activate AutoEnv virtual environment
.\venv\Scripts\activate

# Run test suite
pytest -v
```

### Verified Test Cases
- [x] Valid ZIP extraction with nested folder trees
- [x] ZipSlip directory traversal attack blocked (`../../escaped.txt`)
- [x] ZipSlip absolute path attempt blocked (`/root/evil.sh`)
- [x] Empty archive rejection
- [x] Corrupted archive rejection
- [x] Archive member count threshold (ZipBomb) rejection
- [x] Decompressed size threshold (ZipBomb) rejection
- [x] API health and configuration validation (`/api/health`)
- [x] API project upload with session persistence (`/api/upload`)
- [x] Multi-language detection with `node_modules` and build folder pruning
- [x] Python AST static import extraction without arbitrary code execution
- [x] 3-way dependency classification (Standard Library, Local Modules, External Dependencies)
- [x] Situation A: Validating complete dependency manifests against imports
- [x] Situation B: Automatic dependency reconstruction from source code when no manifest exists
- [x] Situation C: Incomplete manifest detection with missing/unused discrepancy warnings
- [x] Syntax error resilience on invalid Python source files
- [x] Static analysis API endpoint (`POST /api/analyze/{session_id}`)

---

## 🚦 Roadmap

- [x] **Phase 1**: Project architecture + ZIP upload + ZIP validation + extraction
- [x] **Phase 2**: Python language detection + Python AST dependency analysis
- [ ] **Phase 3**: Python import → package resolution
- [ ] **Phase 4**: Python dependency installation in isolated environment
- [ ] **Phase 5**: Python verification (AST syntax & package existence)
- [ ] **Phase 6**: Checkpoint & rollback mechanism
- [ ] **Phase 7**: JavaScript / Node.js support
- [ ] **Phase 8**: Java support
- [ ] **Phase 9**: C# support
- [ ] **Phase 10**: PHP support
- [ ] **Phase 11**: Ruby support
- [ ] **Phase 12**: Go support
- [ ] **Phase 13**: Security hardening & audit
- [ ] **Phase 14**: Automated testing suite
- [ ] **Phase 15**: Final reporting, UI polish & GitHub release
