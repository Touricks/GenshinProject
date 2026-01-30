"""
Incremental Knowledge Graph Extractor.

Tracks file changes and only processes modified files.
Merges KG outputs and handles entity deduplication.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from dataclasses import dataclass

# Handle both package and standalone imports
try:
    from .llm_kg_extractor import (
        KnowledgeGraphOutput,
        ExtractedEntity,
        ExtractedRelationship,
        LLMKnowledgeGraphExtractor,
    )
    from .kg_cache import KGCache
except ImportError:
    from llm_kg_extractor import (
        KnowledgeGraphOutput,
        ExtractedEntity,
        ExtractedRelationship,
        LLMKnowledgeGraphExtractor,
    )
    from kg_cache import KGCache


@dataclass
class FileTrackingInfo:
    """Information about a tracked file."""
    file_path: str
    content_hash: str
    last_processed: str
    entity_count: int
    relationship_count: int


class KGMerger:
    """
    Merge multiple KG outputs with entity deduplication.

    Handles:
    - Alias normalization (杜麦尼→旅行者, 玩家→旅行者)
    - Entity deduplication by normalized name
    - Relationship deduplication by (source, target, type)
    - Merging aliases and roles from multiple sources
    """

    DEFAULT_ALIAS_MAP = {
        "杜麦尼": "旅行者",
        "玩家": "旅行者",
        "Traveler": "旅行者",
    }

    def __init__(self, alias_map: Optional[Dict[str, str]] = None):
        """
        Initialize the merger.

        Args:
            alias_map: Custom alias mapping (defaults to known game aliases)
        """
        self.alias_map = alias_map if alias_map is not None else self.DEFAULT_ALIAS_MAP.copy()

    def normalize_name(self, name: str) -> str:
        """Normalize entity name using alias map."""
        return self.alias_map.get(name, name)

    def add_alias(self, alias: str, canonical: str):
        """Add a new alias mapping."""
        self.alias_map[alias] = canonical

    def merge(self, outputs: List[KnowledgeGraphOutput]) -> KnowledgeGraphOutput:
        """
        Merge multiple KG outputs into one.

        Args:
            outputs: List of KnowledgeGraphOutput objects to merge

        Returns:
            Single merged KnowledgeGraphOutput with deduplicated entities and relationships
        """
        if not outputs:
            return KnowledgeGraphOutput(entities=[], relationships=[])

        # Collect all entities with deduplication
        entities_map: Dict[str, ExtractedEntity] = {}
        for output in outputs:
            for entity in output.entities:
                key = self.normalize_name(entity.name)
                if key not in entities_map:
                    # First occurrence - store with normalized name
                    entities_map[key] = ExtractedEntity(
                        name=key,
                        entity_type=entity.entity_type,
                        role=entity.role,
                        aliases=list(entity.aliases)
                    )
                    # Add original name as alias if different from normalized
                    if entity.name != key and entity.name not in entities_map[key].aliases:
                        entities_map[key].aliases.append(entity.name)
                else:
                    # Merge with existing
                    existing = entities_map[key]
                    # Merge aliases
                    merged_aliases = set(existing.aliases) | set(entity.aliases)
                    if entity.name != key:
                        merged_aliases.add(entity.name)
                    # Keep role if existing doesn't have one
                    merged_role = existing.role or entity.role
                    entities_map[key] = ExtractedEntity(
                        name=key,
                        entity_type=existing.entity_type,
                        role=merged_role,
                        aliases=list(merged_aliases)
                    )

        # Collect all relationships with deduplication
        relationships_set: Set[tuple] = set()
        relationships: List[ExtractedRelationship] = []
        for output in outputs:
            for rel in output.relationships:
                source = self.normalize_name(rel.source)
                target = self.normalize_name(rel.target)
                key = (source, target, rel.relation_type)
                if key not in relationships_set:
                    relationships_set.add(key)
                    relationships.append(ExtractedRelationship(
                        source=source,
                        target=target,
                        relation_type=rel.relation_type,
                        description=rel.description
                    ))

        return KnowledgeGraphOutput(
            entities=list(entities_map.values()),
            relationships=relationships
        )


class IncrementalKGExtractor:
    """
    Incremental Knowledge Graph Extractor.

    Tracks file changes and only processes modified files.
    Supports:
    - File-level change detection via content hash
    - KG merging with entity deduplication
    - Version snapshots
    - Lazy LLM initialization (only loads when needed)
    """

    def __init__(
        self,
        cache_dir: str = ".cache/kg",
        tracking_file: Optional[str] = None
    ):
        """
        Initialize the incremental extractor.

        Args:
            cache_dir: Directory for cache storage
            tracking_file: Path to tracking JSON file (defaults to cache_dir/tracking.json)
        """
        self.cache = KGCache(cache_dir)
        self.tracking_file = Path(tracking_file or f"{cache_dir}/tracking.json")
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        self.merger = KGMerger()
        self._extractor = None
        self.tracking = self._load_tracking()

    @property
    def extractor(self) -> LLMKnowledgeGraphExtractor:
        """Lazy load the LLM extractor."""
        if self._extractor is None:
            self._extractor = LLMKnowledgeGraphExtractor()
        return self._extractor

    def _load_tracking(self) -> Dict[str, FileTrackingInfo]:
        """Load file tracking information from disk."""
        if self.tracking_file.exists():
            try:
                data = json.loads(self.tracking_file.read_text(encoding="utf-8"))
                return {
                    k: FileTrackingInfo(**v)
                    for k, v in data.get("files", {}).items()
                }
            except (json.JSONDecodeError, KeyError, TypeError):
                # Corrupted tracking file, start fresh
                return {}
        return {}

    def _save_tracking(self):
        """Save file tracking information to disk."""
        data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "files": {k: v.__dict__ for k, v in self.tracking.items()}
        }
        self.tracking_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _hash_content(self, content: str) -> str:
        """Calculate MD5 hash of content."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _hash_file(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content."""
        content = file_path.read_text(encoding="utf-8")
        return self._hash_content(content)

    def get_changed_files(self, data_dir: Path, pattern: str = "**/chapter*_dialogue.txt") -> List[Path]:
        """
        Get list of files that have changed since last processing.

        Args:
            data_dir: Directory to scan for files
            pattern: Glob pattern for matching files

        Returns:
            List of file paths that are new or modified
        """
        changed = []
        for file_path in data_dir.glob(pattern):
            file_key = str(file_path)
            current_hash = self._hash_file(file_path)

            if file_key not in self.tracking:
                changed.append(file_path)
            elif self.tracking[file_key].content_hash != current_hash:
                changed.append(file_path)

        return changed

    def extract_file(self, file_path: Path, force: bool = False) -> KnowledgeGraphOutput:
        """
        Extract KG from a single file with caching.

        Args:
            file_path: Path to the dialogue file
            force: If True, bypass cache and re-extract

        Returns:
            KnowledgeGraphOutput for the file
        """
        content = file_path.read_text(encoding="utf-8")

        # Check cache first
        if not force:
            cached = self.cache.get(content)
            if cached is not None:
                return cached

        # Extract using LLM
        result = self.extractor.extract(content)

        # Cache result
        self.cache.set(content, result)

        # Update tracking
        file_key = str(file_path)
        self.tracking[file_key] = FileTrackingInfo(
            file_path=file_key,
            content_hash=self._hash_content(content),
            last_processed=datetime.now().isoformat(),
            entity_count=len(result.entities),
            relationship_count=len(result.relationships)
        )
        self._save_tracking()

        return result

    def extract_changed_files(self, data_dir: Path, pattern: str = "**/chapter*_dialogue.txt") -> List[KnowledgeGraphOutput]:
        """
        Extract KG from only changed files.

        Args:
            data_dir: Directory to scan
            pattern: Glob pattern for files

        Returns:
            List of KnowledgeGraphOutput for changed files only
        """
        changed = self.get_changed_files(data_dir, pattern)
        results = []
        for file_path in changed:
            result = self.extract_file(file_path)
            results.append(result)
        return results

    def extract_all(self, data_dir: Path, pattern: str = "**/chapter*_dialogue.txt", force: bool = False) -> KnowledgeGraphOutput:
        """
        Extract and merge KG from all files.

        Args:
            data_dir: Directory to scan
            pattern: Glob pattern for files
            force: If True, bypass cache for all files

        Returns:
            Single merged KnowledgeGraphOutput
        """
        results = []
        for file_path in sorted(data_dir.glob(pattern)):
            result = self.extract_file(file_path, force=force)
            results.append(result)
        return self.merger.merge(results)

    def extract_incremental(self, data_dir: Path, pattern: str = "**/chapter*_dialogue.txt") -> KnowledgeGraphOutput:
        """
        Incremental extraction: only process changed files, merge with cached results.

        This is the most efficient method for regular updates:
        - New/modified files: Extract via LLM and cache
        - Unchanged files: Use cached results

        Args:
            data_dir: Directory to scan
            pattern: Glob pattern for files

        Returns:
            Single merged KnowledgeGraphOutput
        """
        all_results = []
        for file_path in sorted(data_dir.glob(pattern)):
            content = file_path.read_text(encoding="utf-8")
            cached = self.cache.get(content)
            if cached is not None:
                all_results.append(cached)
            else:
                result = self.extract_file(file_path)
                all_results.append(result)

        return self.merger.merge(all_results)

    def get_status(self) -> Dict[str, Any]:
        """
        Get extraction status.

        Returns:
            Dict with tracking info and cache stats
        """
        return {
            "tracked_files": len(self.tracking),
            "cache_stats": self.cache.get_stats(),
            "files": [
                {
                    "path": info.file_path,
                    "entities": info.entity_count,
                    "relationships": info.relationship_count,
                    "last_processed": info.last_processed
                }
                for info in self.tracking.values()
            ]
        }

    def clear_tracking(self):
        """Clear all tracking information (but keep cache)."""
        self.tracking = {}
        if self.tracking_file.exists():
            self.tracking_file.unlink()

    def save_snapshot(self, output_path: Path, data_dir: Path, pattern: str = "**/chapter*_dialogue.txt") -> KnowledgeGraphOutput:
        """
        Save a merged KG snapshot to file.

        Args:
            output_path: Path to save the snapshot
            data_dir: Directory to extract from
            pattern: Glob pattern for files

        Returns:
            The merged KnowledgeGraphOutput that was saved
        """
        merged = self.extract_incremental(data_dir, pattern)
        output_path.write_text(merged.model_dump_json(indent=2), encoding="utf-8")
        return merged


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import sys

    # Test with sample KG outputs
    print("Testing KGMerger...")
    print("=" * 60)

    kg1 = KnowledgeGraphOutput(
        entities=[
            ExtractedEntity(name="杜麦尼", entity_type="Character"),
            ExtractedEntity(name="派蒙", entity_type="Character"),
        ],
        relationships=[
            ExtractedRelationship(source="杜麦尼", target="派蒙", relation_type="KNOWS"),
        ]
    )

    kg2 = KnowledgeGraphOutput(
        entities=[
            ExtractedEntity(name="旅行者", entity_type="Character", role="主角"),
            ExtractedEntity(name="恰斯卡", entity_type="Character"),
        ],
        relationships=[
            ExtractedRelationship(source="旅行者", target="恰斯卡", relation_type="KNOWS"),
        ]
    )

    merger = KGMerger()
    merged = merger.merge([kg1, kg2])

    print("KG1 entities:", {e.name for e in kg1.entities})
    print("KG2 entities:", {e.name for e in kg2.entities})
    print("Merged entities:", merged.get_entity_names())
    print("Merged relationships:", [(r.source, r.relation_type, r.target) for r in merged.relationships])

    # Check that 杜麦尼 was normalized to 旅行者
    assert "旅行者" in merged.get_entity_names()
    assert "杜麦尼" not in merged.get_entity_names()

    # Check that 旅行者 has 杜麦尼 as alias
    traveler = [e for e in merged.entities if e.name == "旅行者"][0]
    assert "杜麦尼" in traveler.aliases
    assert traveler.role == "主角"

    print("\nAll tests passed!")
