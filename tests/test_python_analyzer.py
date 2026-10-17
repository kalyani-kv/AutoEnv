import pytest
from pathlib import Path

from backend.app.analyzers.detector import LanguageDetector
from backend.app.analyzers.python_analyzer import PythonAnalyzer


def test_language_detector_python_and_js(tmp_path: Path):
    """Test detecting Python and JavaScript while ignoring node_modules and __pycache__."""
    # Create Python files
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "utils.py").write_text("def foo(): pass", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests==2.31.0", encoding="utf-8")

    # Create JavaScript file
    (tmp_path / "index.js").write_text("console.log('hi');", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    # Create ignored directories with files that must NOT be counted
    ignored_nm = tmp_path / "node_modules" / "some_pkg"
    ignored_nm.mkdir(parents=True)
    (ignored_nm / "index.js").write_text("console.log('ignored');", encoding="utf-8")

    ignored_pycache = tmp_path / "__pycache__"
    ignored_pycache.mkdir(parents=True)
    (ignored_pycache / "app.cpython-314.pyc").write_text("binary", encoding="utf-8")

    detector = LanguageDetector()
    res = detector.detect(tmp_path)

    assert res.total_source_files == 3  # 2 python + 1 js (node_modules ignored)
    assert res.primary_language == "Python"
    lang_names = [l.name for l in res.all_detected_languages]
    assert "Python" in lang_names
    assert "JavaScript" in lang_names

    py_info = next(l for l in res.all_detected_languages if l.name == "Python")
    assert py_info.file_count == 2
    assert "requirements.txt" in py_info.manifest_files

    js_info = next(l for l in res.all_detected_languages if l.name == "JavaScript")
    assert js_info.file_count == 1
    assert "package.json" in js_info.manifest_files


def test_stdlib_vs_local_vs_external_classification(tmp_path: Path):
    """
    Test 3-way classification:
    - Standard Library: os, sys, json
    - Local Module: local_helper.py, mypkg/
    - External: requests, numpy
    """
    (tmp_path / "local_helper.py").write_text("def helper(): pass", encoding="utf-8")
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "service.py").write_text("class Service: pass", encoding="utf-8")

    main_code = """
import os
import sys
from json import loads
import requests
import numpy as np
import local_helper
from mypkg.service import Service
from . import relative_mod  # Relative import is local
"""
    (tmp_path / "main.py").write_text(main_code, encoding="utf-8")

    analyzer = PythonAnalyzer()
    res = analyzer.analyze_dependencies(tmp_path)

    # Standard Library check
    assert "os" in res.standard_library_modules
    assert "sys" in res.standard_library_modules
    assert "json" in res.standard_library_modules
    assert "requests" not in res.standard_library_modules

    # Local modules check
    assert "local_helper" in res.local_project_modules
    assert "mypkg" in res.local_project_modules

    # External dependencies check
    ext_names = [d.name for d in res.external_dependencies]
    assert "requests" in ext_names
    assert "numpy" in ext_names
    assert "os" not in ext_names
    assert "local_helper" not in ext_names


def test_situation_b_no_manifest_reconstruction(tmp_path: Path):
    """
    Test Situation B: No requirements.txt or manifest exists.
    AutoEnv must reconstruct external dependencies directly from code.
    """
    (tmp_path / "main.py").write_text("import fastapi\nimport pydantic\nimport math", encoding="utf-8")

    analyzer = PythonAnalyzer()
    res = analyzer.analyze_dependencies(tmp_path)

    assert res.situation.code == "SITUATION_B"
    assert "No dependency manifest found" in res.situation.description
    ext_names = [d.name for d in res.external_dependencies]
    assert "fastapi" in ext_names
    assert "pydantic" in ext_names
    assert "math" in res.standard_library_modules
    assert len(res.declared_dependencies) == 0


def test_situation_a_complete_manifest(tmp_path: Path):
    """
    Test Situation A: requirements.txt exists and matches the source code imports.
    """
    (tmp_path / "main.py").write_text("import requests\nimport os", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests>=2.28.0\n", encoding="utf-8")

    analyzer = PythonAnalyzer()
    res = analyzer.analyze_dependencies(tmp_path)

    assert res.situation.code == "SITUATION_A"
    assert "complete" in res.situation.description.lower()
    assert "requests" in res.declared_dependencies
    assert len(res.missing_from_manifest) == 0
    assert len(res.unused_in_manifest) == 0


def test_situation_c_incomplete_manifest(tmp_path: Path):
    """
    Test Situation C: Manifest has 'flask', but code imports 'requests' and never imports 'flask'.
    - missing_from_manifest: requests
    - unused_in_manifest: flask
    """
    (tmp_path / "main.py").write_text("import requests\nimport sys", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("flask==2.2.0\n", encoding="utf-8")

    analyzer = PythonAnalyzer()
    res = analyzer.analyze_dependencies(tmp_path)

    assert res.situation.code == "SITUATION_C"
    assert "incomplete" in res.situation.description.lower()
    assert "requests" in res.missing_from_manifest
    assert "flask" in res.unused_in_manifest


def test_syntax_error_resilience(tmp_path: Path):
    """
    Test that invalid syntax in one file does not crash the analyzer
    and that the error is recorded cleanly while remaining files are analyzed.
    """
    (tmp_path / "bad.py").write_text("def broken_syntax(:\n   pass", encoding="utf-8")
    (tmp_path / "good.py").write_text("import requests\nimport os", encoding="utf-8")

    analyzer = PythonAnalyzer()
    res = analyzer.analyze_dependencies(tmp_path)

    # Did not crash!
    assert len(res.syntax_errors) == 1
    assert res.syntax_errors[0]["file"] == "bad.py"
    assert res.syntax_errors[0]["line"] > 0

    # Still analyzed good.py
    ext_names = [d.name for d in res.external_dependencies]
    assert "requests" in ext_names
    assert "os" in res.standard_library_modules
