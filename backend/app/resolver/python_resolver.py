from typing import List, Dict, Optional, Any
from .base import (
    ConfidenceLevel,
    ResolvedDependency,
    ResolutionResult,
)
from .known_mappings import lookup_known_mapping
from .pypi_client import PyPIClient
from ..analyzers.base import DependencyItem, DependencyAnalysisResult


class PythonDependencyResolver:
    """
    Multi-tier Python import-to-package resolution engine.
    
    Resolution Tiers:
    1. Manifest Match: Explicitly declared in requirements.txt (1.0 Confidence)
    2. Known Mapping: Curated alias mapping table e.g. cv2 -> opencv-python (1.0 Confidence)
    3. Direct Registry: Direct match on official PyPI registry (0.95 Confidence)
    4. Heuristic Match: Prefixed packages e.g. python-pkg (0.75 Confidence, requires approval)
    5. Unresolved: Ambiguous or not found (0.0 Confidence, blocks blind installation)
    """

    def __init__(self, pypi_client: Optional[PyPIClient] = None):
        self.pypi_client = pypi_client or PyPIClient()

    def resolve_dependency(
        self,
        item: DependencyItem,
        declared_manifest_packages: Optional[Dict[str, Optional[str]]] = None,
    ) -> ResolvedDependency:
        declared_manifest_packages = declared_manifest_packages or {}
        symbol = item.name
        symbol_lower = symbol.lower()

        # Tier 1: Check if already declared in manifest
        for dec_name, dec_ver in declared_manifest_packages.items():
            if dec_name.lower() == symbol_lower:
                return ResolvedDependency(
                    import_symbol=symbol,
                    package_name=dec_name,
                    version_spec=item.version_spec or dec_ver,
                    confidence=ConfidenceLevel.MANIFEST_DECLARED,
                    confidence_score=1.0,
                    resolution_method="manifest_declared",
                    source_files=item.source_files,
                    line_numbers=item.line_numbers,
                    requires_user_approval=False,
                    notes="Package and version explicitly confirmed in project manifest.",
                )

        # Tier 2: Check Curated Known Mapping (e.g. cv2 -> opencv-python, PIL -> Pillow)
        known = lookup_known_mapping(symbol)
        if known:
            return ResolvedDependency(
                import_symbol=symbol,
                package_name=known["package"],
                version_spec=item.version_spec,
                confidence=ConfidenceLevel.EXACT_MAPPING,
                confidence_score=1.0,
                resolution_method="known_mapping",
                source_files=item.source_files,
                line_numbers=item.line_numbers,
                requires_user_approval=False,
                notes=known["notes"],
            )

        # Tier 3: Direct PyPI Registry Match
        pypi_info = self.pypi_client.check_package(symbol)
        if pypi_info.get("exists"):
            canonical = pypi_info.get("canonical_name", symbol)
            latest = pypi_info.get("latest_version")
            return ResolvedDependency(
                import_symbol=symbol,
                package_name=canonical,
                version_spec=item.version_spec,
                confidence=ConfidenceLevel.DIRECT_REGISTRY,
                confidence_score=0.95,
                resolution_method="registry_exact",
                source_files=item.source_files,
                line_numbers=item.line_numbers,
                requires_user_approval=False,
                notes=f"Direct PyPI distribution match verified (latest release: {latest}).",
            )

        # Tier 4: Heuristic Prefix Match (e.g. python-<symbol>)
        heuristic_candidate = f"python-{symbol_lower}"
        heuristic_info = self.pypi_client.check_package(heuristic_candidate)
        if heuristic_info.get("exists"):
            canonical = heuristic_info.get("canonical_name", heuristic_candidate)
            return ResolvedDependency(
                import_symbol=symbol,
                package_name=canonical,
                version_spec=item.version_spec,
                confidence=ConfidenceLevel.HEURISTIC,
                confidence_score=0.75,
                resolution_method="heuristic_prefix",
                source_files=item.source_files,
                line_numbers=item.line_numbers,
                requires_user_approval=True,
                notes=f"Candidate package '{canonical}' found on PyPI via heuristic match. User approval required.",
            )

        # Tier 5: UNRESOLVED — Do NOT guess or blindly install!
        return ResolvedDependency(
            import_symbol=symbol,
            package_name=None,
            version_spec=item.version_spec,
            confidence=ConfidenceLevel.UNRESOLVED,
            confidence_score=0.0,
            resolution_method="unresolved",
            source_files=item.source_files,
            line_numbers=item.line_numbers,
            requires_user_approval=True,
            notes="Dependency detected but package mapping could not be confidently resolved. User review required.",
        )

    def resolve_all(
        self,
        session_id: str,
        analysis_result: DependencyAnalysisResult,
    ) -> ResolutionResult:
        declared_map: Dict[str, Optional[str]] = {}
        for dep_name in analysis_result.declared_dependencies:
            declared_map[dep_name] = None

        resolved_list: List[ResolvedDependency] = []
        unresolved_list: List[ResolvedDependency] = []

        for item in analysis_result.external_dependencies:
            resolved = self.resolve_dependency(item, declared_manifest_packages=declared_map)
            if resolved.confidence in {
                ConfidenceLevel.EXACT_MAPPING,
                ConfidenceLevel.MANIFEST_DECLARED,
                ConfidenceLevel.DIRECT_REGISTRY,
                ConfidenceLevel.HEURISTIC,
            } and resolved.package_name is not None:
                resolved_list.append(resolved)
            else:
                unresolved_list.append(resolved)

        uncertain_count = sum(
            1 for r in resolved_list if r.confidence in {ConfidenceLevel.HEURISTIC, ConfidenceLevel.UNCERTAIN}
        )

        return ResolutionResult(
            session_id=session_id,
            language="Python",
            total_imports=len(analysis_result.external_dependencies),
            resolved_count=len(resolved_list),
            uncertain_count=uncertain_count,
            unresolved_count=len(unresolved_list),
            resolved_dependencies=resolved_list,
            unresolved_dependencies=unresolved_list,
        )
