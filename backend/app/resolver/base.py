from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    EXACT_MAPPING = "CONFIDENT"       # From curated known mapping table (1.0)
    MANIFEST_DECLARED = "CONFIDENT"   # Explicitly declared in requirements.txt (1.0)
    DIRECT_REGISTRY = "CONFIDENT"     # Direct match on PyPI registry (0.95)
    HEURISTIC = "PROBABLE"            # Heuristic match e.g. python-pkg (0.75)
    UNCERTAIN = "UNCERTAIN"           # Ambiguous candidate matches (0.4)
    UNRESOLVED = "UNRESOLVED"         # Could not be resolved (0.0)


class ResolvedDependency(BaseModel):
    import_symbol: str
    package_name: Optional[str] = None
    version_spec: Optional[str] = None
    confidence: ConfidenceLevel
    confidence_score: float = Field(ge=0.0, le=1.0)
    resolution_method: str  # "known_mapping", "manifest", "registry_exact", "unresolved"
    source_files: List[str] = Field(default_factory=list)
    line_numbers: List[int] = Field(default_factory=list)
    requires_user_approval: bool = False
    notes: Optional[str] = None


class ResolutionResult(BaseModel):
    session_id: str
    language: str
    total_imports: int
    resolved_count: int
    uncertain_count: int
    unresolved_count: int
    resolved_dependencies: List[ResolvedDependency]
    unresolved_dependencies: List[ResolvedDependency]
