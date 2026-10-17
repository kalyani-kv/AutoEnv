from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from pydantic import BaseModel, Field


class LanguageInfo(BaseModel):
    name: str
    file_count: int
    percentage: float
    source_files: List[str] = Field(default_factory=list)
    manifest_files: List[str] = Field(default_factory=list)


class LanguageDetectionResult(BaseModel):
    primary_language: Optional[str] = None
    all_detected_languages: List[LanguageInfo] = Field(default_factory=list)
    total_source_files: int = 0
    ignored_directories_encountered: List[str] = Field(default_factory=list)


class ImportOccurrence(BaseModel):
    module_name: str
    source_file: str
    line_number: int


class DependencyItem(BaseModel):
    name: str
    category: str  # "standard_library", "local_module", "external"
    version_spec: Optional[str] = None
    source_files: List[str] = Field(default_factory=list)
    line_numbers: List[int] = Field(default_factory=list)


class AnalysisSituation(BaseModel):
    code: str  # "SITUATION_A", "SITUATION_B", "SITUATION_C"
    description: str


class DependencyAnalysisResult(BaseModel):
    language: str
    situation: AnalysisSituation
    manifest_files: List[str] = Field(default_factory=list)
    declared_dependencies: List[str] = Field(default_factory=list)
    external_dependencies: List[DependencyItem] = Field(default_factory=list)
    standard_library_modules: List[str] = Field(default_factory=list)
    local_project_modules: List[str] = Field(default_factory=list)
    missing_from_manifest: List[str] = Field(default_factory=list)
    unused_in_manifest: List[str] = Field(default_factory=list)
    syntax_errors: List[Dict[str, Any]] = Field(default_factory=list)


class BaseAnalyzer(ABC):
    """Abstract base analyzer for language and dependency detection."""

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Name of the programming language."""
        pass

    @abstractmethod
    def analyze_dependencies(self, project_path: Path) -> DependencyAnalysisResult:
        """Statically inspect project files and return dependency analysis."""
        pass
