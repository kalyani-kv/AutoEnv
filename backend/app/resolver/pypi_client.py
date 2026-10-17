import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
import httpx

from ..config import PROJECT_ROOT

CACHE_DIR = PROJECT_ROOT / ".cache" / "pypi"


def normalize_pep503(name: str) -> str:
    """Normalize package name per PEP 503 (lowercase, dashes instead of underscores/dots)."""
    return re.sub(r"[-_.]+", "-", name).lower()


class PyPIClient:
    """
    Client for querying the official PyPI JSON API.
    Features local disk caching and strict request timeouts.
    """

    def __init__(self, timeout_seconds: float = 5.0, cache_dir: Path = CACHE_DIR):
        self.timeout = timeout_seconds
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    def _get_cache_path(self, normalized_name: str) -> Path:
        return self.cache_dir / f"{normalized_name}.json"

    def _read_cache(self, normalized_name: str) -> Optional[Dict[str, Any]]:
        # Check in-memory cache first
        if normalized_name in self._memory_cache:
            return self._memory_cache[normalized_name]

        # Check disk cache
        cache_path = self._get_cache_path(normalized_name)
        if cache_path.is_file():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                self._memory_cache[normalized_name] = data
                return data
            except Exception:
                pass
        return None

    def _write_cache(self, normalized_name: str, data: Dict[str, Any]) -> None:
        self._memory_cache[normalized_name] = data
        cache_path = self._get_cache_path(normalized_name)
        try:
            cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def check_package(self, package_name: str) -> Dict[str, Any]:
        """
        Queries PyPI to check if package exists and retrieves metadata.
        Returns:
            {
                "exists": bool,
                "canonical_name": str,
                "latest_version": Optional[str],
                "summary": Optional[str],
                "from_cache": bool
            }
        """
        normalized = normalize_pep503(package_name)

        # 1. Check cache
        cached = self._read_cache(normalized)
        if cached is not None:
            cached_copy = dict(cached)
            cached_copy["from_cache"] = True
            return cached_copy

        url = f"https://pypi.org/pypi/{normalized}/json"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers={"User-Agent": "AutoEnv-Resolver/0.1.0"})

            if response.status_code == 200:
                body = response.json()
                info = body.get("info", {})
                result = {
                    "exists": True,
                    "canonical_name": info.get("name", package_name),
                    "latest_version": info.get("version"),
                    "summary": info.get("summary", ""),
                    "home_page": info.get("home_page", ""),
                    "from_cache": False,
                }
                self._write_cache(normalized, result)
                return result

            elif response.status_code == 404:
                result = {
                    "exists": False,
                    "canonical_name": package_name,
                    "latest_version": None,
                    "summary": None,
                    "from_cache": False,
                }
                self._write_cache(normalized, result)
                return result
            else:
                return {
                    "exists": False,
                    "canonical_name": package_name,
                    "error": f"PyPI returned HTTP {response.status_code}",
                    "from_cache": False,
                }

        except Exception as exc:
            # Network failure or timeout - do not crash
            return {
                "exists": False,
                "canonical_name": package_name,
                "error": f"Network error querying PyPI: {exc}",
                "from_cache": False,
            }
