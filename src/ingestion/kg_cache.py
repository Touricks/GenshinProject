"""
Knowledge Graph Cache Module.

Caches LLM extraction results to avoid redundant API calls.
Cache is based on content hash, so identical text always returns cached results.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Handle both package and standalone imports
try:
    from .llm_kg_extractor import KnowledgeGraphOutput
except ImportError:
    from llm_kg_extractor import KnowledgeGraphOutput


class KGCache:
    """
    Cache for Knowledge Graph extraction results.

    Stores extraction results as JSON files, keyed by content hash.
    This allows incremental processing and avoids redundant LLM calls.
    """

    def __init__(self, cache_dir: str = ".cache/kg"):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._stats = {"hits": 0, "misses": 0}

    def _hash_text(self, text: str) -> str:
        """Generate MD5 hash of text content."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _get_cache_path(self, text_hash: str) -> Path:
        """Get cache file path for a given hash."""
        return self.cache_dir / f"{text_hash}.json"

    def get(self, text: str) -> Optional[KnowledgeGraphOutput]:
        """
        Get cached extraction result for text.

        Args:
            text: Input text to look up

        Returns:
            KnowledgeGraphOutput if cached, None otherwise
        """
        text_hash = self._hash_text(text)
        cache_path = self._get_cache_path(text_hash)

        if cache_path.exists():
            try:
                content = cache_path.read_text(encoding="utf-8")
                data = json.loads(content)
                # Extract just the result part (metadata is stored too)
                result_data = data.get("result", data)
                self._stats["hits"] += 1
                return KnowledgeGraphOutput.model_validate(result_data)
            except (json.JSONDecodeError, ValueError) as e:
                # Corrupted cache file, remove it
                cache_path.unlink(missing_ok=True)

        self._stats["misses"] += 1
        return None

    def set(self, text: str, result: KnowledgeGraphOutput, metadata: Optional[Dict[str, Any]] = None):
        """
        Cache extraction result for text.

        Args:
            text: Input text
            result: Extraction result to cache
            metadata: Optional metadata to store with the result
        """
        text_hash = self._hash_text(text)
        cache_path = self._get_cache_path(text_hash)

        cache_data = {
            "hash": text_hash,
            "cached_at": datetime.now().isoformat(),
            "text_length": len(text),
            "text_preview": text[:200] + "..." if len(text) > 200 else text,
            "result": result.model_dump(),
            "metadata": metadata or {}
        }

        cache_path.write_text(
            json.dumps(cache_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def has(self, text: str) -> bool:
        """Check if text is cached without loading the result."""
        text_hash = self._hash_text(text)
        return self._get_cache_path(text_hash).exists()

    def invalidate(self, text: str) -> bool:
        """
        Remove cached result for text.

        Args:
            text: Input text to invalidate

        Returns:
            True if cache was removed, False if not found
        """
        text_hash = self._hash_text(text)
        cache_path = self._get_cache_path(text_hash)

        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def clear(self):
        """Clear all cached results."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        self._stats = {"hits": 0, "misses": 0}

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": self._stats["hits"] / max(1, self._stats["hits"] + self._stats["misses"]),
            "cached_items": len(cache_files),
            "total_size_bytes": total_size,
            "cache_dir": str(self.cache_dir)
        }

    def list_cached(self) -> list[Dict[str, Any]]:
        """List all cached items with metadata."""
        items = []
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                items.append({
                    "hash": data.get("hash", cache_file.stem),
                    "cached_at": data.get("cached_at"),
                    "text_preview": data.get("text_preview", ""),
                    "entity_count": len(data.get("result", {}).get("entities", [])),
                    "relationship_count": len(data.get("result", {}).get("relationships", []))
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return items


class CachedKGExtractor:
    """
    Knowledge Graph Extractor with caching support.

    Wraps LLMKnowledgeGraphExtractor to add transparent caching.
    """

    def __init__(self, cache_dir: str = ".cache/kg"):
        """
        Initialize cached extractor.

        Args:
            cache_dir: Directory for cache storage
        """
        from .llm_kg_extractor import LLMKnowledgeGraphExtractor

        self.cache = KGCache(cache_dir)
        self._extractor = None  # Lazy initialization

    @property
    def extractor(self):
        """Lazy load the LLM extractor."""
        if self._extractor is None:
            from .llm_kg_extractor import LLMKnowledgeGraphExtractor
            self._extractor = LLMKnowledgeGraphExtractor()
        return self._extractor

    def extract(self, text: str, force_refresh: bool = False) -> KnowledgeGraphOutput:
        """
        Extract KG with caching.

        Args:
            text: Input text
            force_refresh: If True, bypass cache and re-extract

        Returns:
            KnowledgeGraphOutput
        """
        if not force_refresh:
            cached = self.cache.get(text)
            if cached is not None:
                return cached

        # Extract using LLM
        result = self.extractor.extract(text)

        # Cache the result
        self.cache.set(text, result)

        return result

    def extract_file(self, file_path: Path, force_refresh: bool = False) -> KnowledgeGraphOutput:
        """
        Extract KG from file with caching.

        Args:
            file_path: Path to dialogue file
            force_refresh: If True, bypass cache

        Returns:
            KnowledgeGraphOutput
        """
        text = file_path.read_text(encoding="utf-8")
        return self.extract(text, force_refresh=force_refresh)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()


# =============================================================================
# CLI for cache management
# =============================================================================

if __name__ == "__main__":
    import sys

    cache = KGCache()

    if len(sys.argv) < 2:
        print("Usage: python kg_cache.py [stats|list|clear]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "stats":
        stats = cache.get_stats()
        print("Cache Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    elif command == "list":
        items = cache.list_cached()
        print(f"Cached Items ({len(items)}):")
        for item in items:
            print(f"  [{item['hash'][:8]}] {item['entity_count']} entities, "
                  f"{item['relationship_count']} relationships")
            print(f"    Preview: {item['text_preview'][:60]}...")

    elif command == "clear":
        cache.clear()
        print("Cache cleared.")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
