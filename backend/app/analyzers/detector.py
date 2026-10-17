import os
from pathlib import Path
from typing import Dict, List, Set
from ..config import IGNORED_DIRECTORIES
from .base import LanguageInfo, LanguageDetectionResult

# Language signature mapping (extensions and configuration manifests)
LANGUAGE_SPECS = {
    "Python": {
        "extensions": {".py", ".pyw"},
        "manifests": {"requirements.txt", "setup.py", "pyproject.toml", "pipfile", "environment.yml"},
    },
    "JavaScript": {
        "extensions": {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"},
        "manifests": {"package.json", "package-lock.json", "yarn.lock"},
    },
    "Java": {
        "extensions": {".java"},
        "manifests": {"pom.xml", "build.gradle", "build.gradle.kts"},
    },
    "C#": {
        "extensions": {".cs"},
        "manifest_suffixes": {".csproj", ".sln"},
        "manifests": {"nuget.config"},
    },
    "PHP": {
        "extensions": {".php"},
        "manifests": {"composer.json", "composer.lock"},
    },
    "Ruby": {
        "extensions": {".rb"},
        "manifests": {"gemfile", "gemfile.lock"},
    },
    "Go": {
        "extensions": {".go"},
        "manifests": {"go.mod", "go.sum"},
    },
}


class LanguageDetector:
    """
    Statically detects programming languages and dependency manifests in a project folder.
    Strictly ignores build artifacts, virtual environments, and cache directories.
    """

    def __init__(self, ignored_dirs: Set[str] = IGNORED_DIRECTORIES):
        self.ignored_dirs = {d.lower() for d in ignored_dirs}

    def detect(self, project_path: Path) -> LanguageDetectionResult:
        lang_files: Dict[str, List[str]] = {lang: [] for lang in LANGUAGE_SPECS}
        lang_manifests: Dict[str, List[str]] = {lang: [] for lang in LANGUAGE_SPECS}
        encountered_ignored: Set[str] = set()
        total_source_files = 0

        resolved_root = project_path.resolve()

        for root, dirs, files in os.walk(resolved_root):
            # Prune ignored directories in-place so os.walk does not descend into them
            pruned_dirs = []
            for d in dirs:
                if d.lower() in self.ignored_dirs:
                    encountered_ignored.add(d)
                else:
                    pruned_dirs.append(d)
            dirs[:] = pruned_dirs

            current_dir_path = Path(root)

            for filename in files:
                file_path = current_dir_path / filename
                rel_path = str(file_path.relative_to(resolved_root)).replace("\\", "/")
                file_lower = filename.lower()
                suffix_lower = file_path.suffix.lower()

                for lang, spec in LANGUAGE_SPECS.items():
                    # Check file extensions
                    if suffix_lower in spec.get("extensions", set()):
                        lang_files[lang].append(rel_path)
                        total_source_files += 1

                    # Check exact manifest file names
                    if file_lower in spec.get("manifests", set()):
                        lang_manifests[lang].append(rel_path)

                    # Check manifest suffixes (like .csproj)
                    for suf in spec.get("manifest_suffixes", set()):
                        if file_lower.endswith(suf):
                            lang_manifests[lang].append(rel_path)

        # Build detected language summaries
        detected_languages: List[LanguageInfo] = []
        for lang, files in lang_files.items():
            manifests = lang_manifests[lang]
            if files or manifests:
                pct = (len(files) / total_source_files * 100) if total_source_files > 0 else 0.0
                detected_languages.append(
                    LanguageInfo(
                        name=lang,
                        file_count=len(files),
                        percentage=round(pct, 1),
                        source_files=files,
                        manifest_files=manifests,
                    )
                )

        # Sort languages by file count descending
        detected_languages.sort(key=lambda x: x.file_count, reverse=True)
        primary_lang = detected_languages[0].name if detected_languages else None

        return LanguageDetectionResult(
            primary_language=primary_lang,
            all_detected_languages=detected_languages,
            total_source_files=total_source_files,
            ignored_directories_encountered=sorted(encountered_ignored),
        )
