import pytest
from pathlib import Path
from unittest.mock import MagicMock

from backend.app.resolver.base import ConfidenceLevel
from backend.app.resolver.known_mappings import lookup_known_mapping
from backend.app.resolver.pypi_client import normalize_pep503, PyPIClient
from backend.app.resolver.python_resolver import PythonDependencyResolver
from backend.app.analyzers.base import DependencyItem, DependencyAnalysisResult, AnalysisSituation


def test_normalize_pep503():
    """Test PEP 503 package name normalization."""
    assert normalize_pep503("OpenCV_Python") == "opencv-python"
    assert normalize_pep503("Scikit.Learn") == "scikit-learn"
    assert normalize_pep503("python_dotenv") == "python-dotenv"


def test_known_mappings_lookup():
    """Test looking up famous Python alias discrepancies."""
    cv2_map = lookup_known_mapping("cv2")
    assert cv2_map is not None
    assert cv2_map["package"] == "opencv-python"

    pil_map = lookup_known_mapping("PIL")
    assert pil_map is not None
    assert pil_map["package"] == "Pillow"

    bs4_map = lookup_known_mapping("bs4")
    assert bs4_map is not None
    assert bs4_map["package"] == "beautifulsoup4"

    yaml_map = lookup_known_mapping("yaml")
    assert yaml_map is not None
    assert yaml_map["package"] == "PyYAML"

    sklearn_map = lookup_known_mapping("sklearn")
    assert sklearn_map is not None
    assert sklearn_map["package"] == "scikit-learn"


def test_resolver_with_known_mapping():
    """Test that resolver correctly routes known aliases without hitting network."""
    mock_client = MagicMock(spec=PyPIClient)
    resolver = PythonDependencyResolver(pypi_client=mock_client)

    item = DependencyItem(name="cv2", category="external", source_files=["main.py"], line_numbers=[1])
    resolved = resolver.resolve_dependency(item)

    assert resolved.package_name == "opencv-python"
    assert resolved.confidence == ConfidenceLevel.EXACT_MAPPING
    assert resolved.confidence_score == 1.0
    assert resolved.resolution_method == "known_mapping"
    assert not resolved.requires_user_approval
    # Verify network was not called for known mapping
    mock_client.check_package.assert_not_called()


def test_resolver_with_manifest_match():
    """Test that resolver uses manifest declaration when present."""
    mock_client = MagicMock(spec=PyPIClient)
    resolver = PythonDependencyResolver(pypi_client=mock_client)

    item = DependencyItem(name="requests", category="external", version_spec=">=2.28.0")
    resolved = resolver.resolve_dependency(item, declared_manifest_packages={"requests": ">=2.28.0"})

    assert resolved.package_name == "requests"
    assert resolved.version_spec == ">=2.28.0"
    assert resolved.confidence == ConfidenceLevel.MANIFEST_DECLARED
    assert resolved.confidence_score == 1.0
    assert resolved.resolution_method == "manifest_declared"


def test_resolver_direct_registry_match():
    """Test resolving a package directly against PyPI mock."""
    mock_client = MagicMock(spec=PyPIClient)
    mock_client.check_package.return_value = {
        "exists": True,
        "canonical_name": "fastapi",
        "latest_version": "0.115.0",
        "summary": "FastAPI framework",
    }
    resolver = PythonDependencyResolver(pypi_client=mock_client)

    item = DependencyItem(name="fastapi", category="external")
    resolved = resolver.resolve_dependency(item)

    assert resolved.package_name == "fastapi"
    assert resolved.confidence == ConfidenceLevel.DIRECT_REGISTRY
    assert resolved.confidence_score == 0.95
    assert resolved.resolution_method == "registry_exact"
    mock_client.check_package.assert_called_with("fastapi")


def test_resolver_unresolved_package():
    """
    CRITICAL RULE TEST: If a package cannot be confidently resolved,
    AutoEnv must NOT guess or install random packages.
    It must report UNRESOLVED with requires_user_approval = True.
    """
    mock_client = MagicMock(spec=PyPIClient)
    # Neither direct nor heuristic exists
    mock_client.check_package.return_value = {"exists": False}
    resolver = PythonDependencyResolver(pypi_client=mock_client)

    item = DependencyItem(name="unknown_internal_lib", category="external")
    resolved = resolver.resolve_dependency(item)

    assert resolved.package_name is None
    assert resolved.confidence == ConfidenceLevel.UNRESOLVED
    assert resolved.confidence_score == 0.0
    assert resolved.resolution_method == "unresolved"
    assert resolved.requires_user_approval is True
    assert "could not be confidently resolved" in resolved.notes
