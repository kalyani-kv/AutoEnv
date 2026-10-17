import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

try:
    import tomllib  # Python 3.11+ standard library
except ImportError:
    tomllib = None

from ..config import IGNORED_DIRECTORIES
from .base import (
    BaseAnalyzer,
    DependencyAnalysisResult,
    DependencyItem,
    AnalysisSituation,
)

# Standard library modules set
_STDLIB_MODULES: Set[str] = set()
if hasattr(sys, "stdlib_module_names"):
    _STDLIB_MODULES = set(sys.stdlib_module_names)
else:
    # Comprehensive fallback for Python standard library
    _STDLIB_MODULES = {
        "abc", "argparse", "array", "ast", "asynchat", "asyncio", "asyncore", "atexit",
        "audioop", "base64", "bdb", "binascii", "binhex", "bisect", "builtins", "bz2",
        "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code", "codecs", "codeop",
        "collections", "colorsys", "compileall", "concurrent", "configparser", "contextlib",
        "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses",
        "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis", "distutils", "doctest",
        "email", "encodings", "ensurepip", "enum", "errno", "faulthandler", "fcntl", "filecmp",
        "fileinput", "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt", "getpass",
        "gettext", "glob", "graphlib", "grp", "gzip", "hashlib", "heapq", "hmac", "html",
        "http", "imaplib", "imghdr", "imp", "importlib", "inspect", "io", "ipaddress",
        "itertools", "json", "keyword", "lib2to3", "linecache", "locale", "logging", "lzma",
        "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap", "modulefinder", "msilib",
        "msvcrt", "multiprocessing", "netrc", "nis", "nntplib", "numbers", "operator", "optparse",
        "os", "ossaudiodev", "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
        "platform", "plistlib", "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
        "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random", "re",
        "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
        "selectors", "shelve", "shlex", "shutil", "signal", "site", "smtpd", "smtplib",
        "sndhdr", "socket", "socketserver", "spwd", "sqlite3", "ssl", "stat", "statistics",
        "string", "stringprep", "struct", "subprocess", "sunau", "symbol", "symtable", "sys",
        "sysconfig", "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile", "termios",
        "test", "textwrap", "threading", "time", "timeit", "tkinter", "token", "tokenize",
        "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types",
        "typing", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv", "warnings",
        "wave", "weakref", "webbrowser", "winreg", "winsound", "wsgiref", "xdrlib", "xml",
        "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib"
    }

# Include builtin modules (e.g. `_io`, `_thread`)
_STDLIB_MODULES.update(sys.builtin_module_names)


class PythonAnalyzer(BaseAnalyzer):
    """
    Static analyzer for Python projects.
    Extracts imports using Python AST without executing any project code.
    Classifies imports into Standard Library, Local Project Module, or External Dependency.
    """

    @property
    def language_name(self) -> str:
        return "Python"

    def _discover_local_modules(self, project_path: Path) -> Set[str]:
        """
        Scans project directory for local Python files and subpackages.
        Any module matching these stems or folders is classified as a local module.
        """
        local_modules: Set[str] = set()
        resolved_root = project_path.resolve()

        for root, dirs, files in os.walk(resolved_root):
            # Exclude ignored directories
            dirs[:] = [d for d in dirs if d.lower() not in {x.lower() for x in IGNORED_DIRECTORIES}]

            curr_dir = Path(root)
            rel_dir = curr_dir.relative_to(resolved_root)

            # Top-level folders or subpackages
            if rel_dir == Path("."):
                for d in dirs:
                    local_modules.add(d)
                # Also check src/ folder if present
                if "src" in dirs:
                    src_dir = resolved_root / "src"
                    if src_dir.is_dir():
                        for item in src_dir.iterdir():
                            local_modules.add(item.stem)
            else:
                # Add folder name if it's a package
                if "__init__.py" in files:
                    local_modules.add(curr_dir.name)

            for f in files:
                if f.endswith((".py", ".pyw")):
                    stem = Path(f).stem
                    local_modules.add(stem)

        return local_modules

    def _parse_requirements_txt(self, req_path: Path) -> Dict[str, Optional[str]]:
        """
        Parses requirements.txt for declared package names and version specifiers.
        Handles comments, environment markers, and flags safely.
        """
        declared: Dict[str, Optional[str]] = {}
        if not req_path.is_file():
            return declared

        try:
            content = req_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return declared

        for line in content.splitlines():
            line = line.strip()
            # Ignore comments, empty lines, and pip flags (-r, -i, etc.)
            if not line or line.startswith(("#", "-", "--")):
                continue

            # Strip inline comments
            if " #" in line:
                line = line.split(" #", 1)[0].strip()

            # Strip environment markers (; sys_platform == '...')
            if ";" in line:
                line = line.split(";", 1)[0].strip()

            # Match package name and optional version specification
            # Examples: requests>=2.28.0, flask==2.0.1, numpy, urllib3<2.0
            match = re.match(r"^([A-Za-z0-9_.\-]+)\s*(.*)$", line)
            if match:
                pkg_name = match.group(1).strip()
                version_spec = match.group(2).strip() or None
                declared[pkg_name] = version_spec

        return declared

    def _parse_pyproject_toml(self, toml_path: Path) -> Dict[str, Optional[str]]:
        """Parses pyproject.toml for dependencies if tomllib is available."""
        declared: Dict[str, Optional[str]] = {}
        if not toml_path.is_file() or tomllib is None:
            return declared

        try:
            content = toml_path.read_text(encoding="utf-8", errors="ignore")
            data = tomllib.loads(content)

            # PEP 621 project.dependencies
            project_deps = data.get("project", {}).get("dependencies", [])
            for dep in project_deps:
                match = re.match(r"^([A-Za-z0-9_.\-]+)\s*(.*)$", dep.strip())
                if match:
                    declared[match.group(1)] = match.group(2) or None

            # Poetry dependencies
            poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
            for pkg, ver in poetry_deps.items():
                if pkg.lower() != "python":
                    declared[pkg] = str(ver) if ver else None
        except Exception:
            pass

        return declared

    def analyze_dependencies(self, project_path: Path) -> DependencyAnalysisResult:
        resolved_root = project_path.resolve()
        local_modules = self._discover_local_modules(resolved_root)

        # Track occurrences: module_name -> list of (file, line)
        import_occurrences: Dict[str, List[Tuple[str, int]]] = {}
        syntax_errors: List[Dict[str, Any]] = []

        # Find all Python files
        for root, dirs, files in os.walk(resolved_root):
            dirs[:] = [d for d in dirs if d.lower() not in {x.lower() for x in IGNORED_DIRECTORIES}]
            for file in files:
                if not file.endswith((".py", ".pyw")):
                    continue

                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(resolved_root)).replace("\\", "/")

                try:
                    code_bytes = full_path.read_bytes()
                    tree = ast.parse(code_bytes, filename=rel_path)
                except SyntaxError as exc:
                    syntax_errors.append({
                        "file": rel_path,
                        "line": exc.lineno or 0,
                        "message": str(exc.msg),
                    })
                    continue
                except Exception as exc:
                    syntax_errors.append({
                        "file": rel_path,
                        "line": 0,
                        "message": f"Read/Parse error: {exc}",
                    })
                    continue

                # Visit import nodes statically
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            top_level = alias.name.split(".")[0]
                            import_occurrences.setdefault(top_level, []).append((rel_path, node.lineno))

                    elif isinstance(node, ast.ImportFrom):
                        # Relative imports (level > 0, e.g. `from . import foo`) are strictly local
                        if node.level > 0:
                            if node.module:
                                top_level = node.module.split(".")[0]
                                import_occurrences.setdefault(top_level, []).append((rel_path, node.lineno))
                            continue

                        # Absolute imports (level == 0)
                        if node.module:
                            top_level = node.module.split(".")[0]
                            import_occurrences.setdefault(top_level, []).append((rel_path, node.lineno))

        # Check existing dependency manifests
        manifest_files: List[str] = []
        declared_packages: Dict[str, Optional[str]] = {}

        req_txt = resolved_root / "requirements.txt"
        if req_txt.is_file():
            manifest_files.append("requirements.txt")
            declared_packages.update(self._parse_requirements_txt(req_txt))

        pyproject = resolved_root / "pyproject.toml"
        if pyproject.is_file():
            manifest_files.append("pyproject.toml")
            declared_packages.update(self._parse_pyproject_toml(pyproject))

        for extra_manifest in ["setup.py", "Pipfile"]:
            if (resolved_root / extra_manifest).is_file():
                manifest_files.append(extra_manifest)

        # 3-Way Classification
        stdlib_modules: Set[str] = set()
        local_mods: Set[str] = set()
        external_deps: Dict[str, DependencyItem] = {}
        local_modules_lower = {m.lower(): m for m in local_modules}

        for mod_name, occurrences in import_occurrences.items():
            mod_lower = mod_name.lower()

            if mod_name in _STDLIB_MODULES or mod_lower in _STDLIB_MODULES:
                stdlib_modules.add(mod_name)
            elif mod_lower in local_modules_lower:
                local_mods.add(local_modules_lower[mod_lower])
            else:
                # External dependency requiring package resolution
                src_files = sorted({src for src, _ in occurrences})
                lines = [ln for _, ln in occurrences]
                external_deps[mod_name] = DependencyItem(
                    name=mod_name,
                    category="external",
                    version_spec=declared_packages.get(mod_name) or declared_packages.get(mod_lower),
                    source_files=src_files,
                    line_numbers=sorted(lines),
                )

        # Compare declared manifest vs detected imports
        declared_names_list = list(declared_packages.keys())
        declared_lower_set = {pkg.lower(): pkg for pkg in declared_packages}
        detected_external_lower = {name.lower(): name for name in external_deps}

        missing_from_manifest: List[str] = []
        for det_lower, orig_name in detected_external_lower.items():
            # If imported external module is not in declared manifest
            if det_lower not in declared_lower_set:
                missing_from_manifest.append(orig_name)

        unused_in_manifest: List[str] = []
        for dec_lower, orig_name in declared_lower_set.items():
            # If declared in manifest but never imported
            if dec_lower not in detected_external_lower:
                unused_in_manifest.append(orig_name)

        # Determine Situation A, B, or C
        if not manifest_files:
            situation = AnalysisSituation(
                code="SITUATION_B",
                description="No dependency manifest found. External dependencies were reconstructed directly from source code AST imports.",
            )
        elif missing_from_manifest or unused_in_manifest:
            situation = AnalysisSituation(
                code="SITUATION_C",
                description="Dependency manifest exists but is incomplete or has discrepancies compared with code imports.",
            )
        else:
            situation = AnalysisSituation(
                code="SITUATION_A",
                description="Dependency manifest exists and is complete. Declared dependencies match source code imports.",
            )

        return DependencyAnalysisResult(
            language="Python",
            situation=situation,
            manifest_files=manifest_files,
            declared_dependencies=declared_names_list,
            external_dependencies=list(external_deps.values()),
            standard_library_modules=sorted(stdlib_modules),
            local_project_modules=sorted(local_modules),
            missing_from_manifest=sorted(missing_from_manifest),
            unused_in_manifest=sorted(unused_in_manifest),
            syntax_errors=syntax_errors,
        )
