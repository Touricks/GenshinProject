"""
Incremental Knowledge Graph Extractor.

Tracks file changes and extracts entities/relationships from dialogue files.
Provides incremental processing with file change tracking and caching.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass, asdict

from .llm_kg_extractor import (
    LLMKnowledgeGraphExtractor,
    KnowledgeGraphOutput,
    ExtractedEntity,
    ExtractedRelationship,
)


@dataclass
class KGFileTrackingInfo:
    """Tracking information for a processed file."""

    file_path: str
    content_hash: str
    last_processed: str
    entity_count: int
    relationship_count: int
    task_id: str
    chapter: int


class KGCache:
    """Simple content-addressed cache for KG extraction results."""

    def __init__(self, cache_dir: str = ".cache/kg"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_key(self, content: str) -> str:
        """Generate cache key from content hash."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def get(self, content: str) -> Optional[KnowledgeGraphOutput]:
        """Get cached result for content."""
        key = self._hash_key(content)
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                # Handle legacy cache format with "result" wrapper
                if "result" in data:
                    data = data["result"]
                return KnowledgeGraphOutput(**data)
            except (json.JSONDecodeError, KeyError, TypeError):
                return None
        return None

    def set(self, content: str, result: KnowledgeGraphOutput):
        """Cache extraction result."""
        key = self._hash_key(content)
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob("*.json"))
        return {
            "cache_dir": str(self.cache_dir),
            "cached_files": len(cache_files),
        }


class IncrementalKGExtractor:
    """
    Incremental Knowledge Graph Extractor.

    Tracks file changes and only processes modified files.
    Extracts entities and relationships for building the knowledge graph.

    Usage:
        extractor = IncrementalKGExtractor()

        # Extract KG from a single folder
        results = extractor.extract_folder(Path("Data/Archon/1608"))

        # Extract from all data
        all_results = extractor.extract_all(Path("Data/"))

        # Write to graph
        from src.graph.builder import GraphBuilder
        with GraphBuilder() as builder:
            for result in all_results:
                builder.ingest_kg_extraction(
                    entities=result["entities"],
                    relationships=result["relationships"],
                    chapter=result["chapter"],
                    task_id=result["task_id"],
                )
    """

    def __init__(
        self,
        cache_dir: str = ".cache/kg",
        tracking_file: Optional[str] = None,
    ):
        """
        Initialize the incremental KG extractor.

        Args:
            cache_dir: Directory for cache storage
            tracking_file: Path to tracking JSON file
        """
        self.cache = KGCache(cache_dir)
        self.tracking_file = Path(tracking_file or f"{cache_dir}/kg_tracking.json")
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        self._extractor = None
        self.tracking = self._load_tracking()

    @property
    def extractor(self) -> LLMKnowledgeGraphExtractor:
        """Lazy load the LLM extractor."""
        if self._extractor is None:
            self._extractor = LLMKnowledgeGraphExtractor()
        return self._extractor

    def _load_tracking(self) -> Dict[str, KGFileTrackingInfo]:
        """Load file tracking information from disk."""
        if self.tracking_file.exists():
            try:
                data = json.loads(self.tracking_file.read_text(encoding="utf-8"))
                return {
                    k: KGFileTrackingInfo(**v)
                    for k, v in data.get("files", {}).items()
                }
            except (json.JSONDecodeError, KeyError, TypeError):
                return {}
        return {}

    def _save_tracking(self):
        """Save file tracking information to disk."""
        data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "files": {k: asdict(v) for k, v in self.tracking.items()},
        }
        self.tracking_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _hash_content(self, content: str) -> str:
        """Calculate MD5 hash of content."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _hash_file(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content."""
        content = file_path.read_text(encoding="utf-8")
        return self._hash_content(content)

    def _parse_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse task_id and chapter from file path.

        Expected structure: Data/Archon/{task_id}/chapter{N}_dialogue.txt
        Returns: {"task_id": "1608", "chapter": 160800, "chapter_num": 0}
        """
        # Extract task_id from parent folder name
        task_id = file_path.parent.name

        # Extract chapter number from filename
        match = re.search(r"chapter(\d+)", file_path.stem)
        chapter_num = int(match.group(1)) if match else 0

        # Calculate GlobalChapter = TaskID * 100 + ChapterNum
        try:
            global_chapter = int(task_id) * 100 + chapter_num
        except ValueError:
            global_chapter = chapter_num

        return {
            "task_id": task_id,
            "chapter": global_chapter,
            "chapter_num": chapter_num,
        }

    def get_changed_files(
        self,
        data_dir: Path,
        pattern: str = "**/chapter*_dialogue.txt",
    ) -> List[Path]:
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

    def extract_file(
        self,
        file_path: Path,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Extract KG from a single file with caching.

        Tracking is updated immediately after processing each file to prevent
        data loss if extraction is interrupted.

        Args:
            file_path: Path to the dialogue file
            force: If True, bypass cache and re-extract

        Returns:
            Dict with keys: entities, relationships, task_id, chapter, file_path
        """
        content = file_path.read_text(encoding="utf-8")
        content_hash = self._hash_content(content)
        metadata = self._parse_file_metadata(file_path)
        file_key = str(file_path)

        # Check cache first
        cached = None
        if not force:
            cached = self.cache.get(content)

        # Fast path: file unchanged and cached - skip processing
        if not force and file_key in self.tracking:
            if self.tracking[file_key].content_hash == content_hash and cached is not None:
                return {
                    "entities": cached.entities,
                    "relationships": cached.relationships,
                    "task_id": metadata["task_id"],
                    "chapter": metadata["chapter"],
                    "file_path": file_key,
                }

        if cached is not None:
            # Use cached result
            entities = cached.entities
            relationships = cached.relationships
        else:
            # Extract using LLM
            result = self.extractor.extract(content)

            # Cache result immediately
            self.cache.set(content, result)
            entities = result.entities
            relationships = result.relationships

        # Update tracking immediately after extraction/cache hit
        self.tracking[file_key] = KGFileTrackingInfo(
            file_path=file_key,
            content_hash=content_hash,
            last_processed=datetime.now().isoformat(),
            entity_count=len(entities),
            relationship_count=len(relationships),
            task_id=metadata["task_id"],
            chapter=metadata["chapter"],
        )
        self._save_tracking()

        return {
            "entities": entities,
            "relationships": relationships,
            "task_id": metadata["task_id"],
            "chapter": metadata["chapter"],
            "file_path": file_key,
        }

    def extract_folder(
        self,
        folder_path: Path,
        force: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Extract KG from all dialogue files in a folder.

        Args:
            folder_path: Path to folder (e.g., Data/Archon/1608)
            force: If True, bypass cache

        Returns:
            List of extraction results
        """
        results = []
        dialogue_files = sorted(folder_path.glob("chapter*_dialogue.txt"))

        for file_path in dialogue_files:
            print(f"Processing: {file_path.name}...")
            result = self.extract_file(file_path, force=force)
            results.append(result)
            print(f"  Extracted {len(result['entities'])} entities, {len(result['relationships'])} relationships")

        return results

    def extract_all(
        self,
        data_dir: Path,
        pattern: str = "**/chapter*_dialogue.txt",
        force: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Extract KG from all dialogue files.

        Args:
            data_dir: Root data directory
            pattern: Glob pattern for files
            force: If True, bypass cache

        Returns:
            List of extraction results for all files
        """
        results = []
        for file_path in sorted(data_dir.glob(pattern)):
            result = self.extract_file(file_path, force=force)
            results.append(result)
        return results

    def extract_incremental(
        self,
        data_dir: Path,
        pattern: str = "**/chapter*_dialogue.txt",
    ) -> List[Dict[str, Any]]:
        """
        Incremental extraction: only process changed files.

        Args:
            data_dir: Root data directory
            pattern: Glob pattern for files

        Returns:
            List of extraction results for changed files only
        """
        changed = self.get_changed_files(data_dir, pattern)
        results = []

        print(f"Found {len(changed)} changed files to process")
        for file_path in changed:
            print(f"Processing: {file_path}...")
            result = self.extract_file(file_path)
            results.append(result)
            print(f"  Extracted {len(result['entities'])} entities, {len(result['relationships'])} relationships")

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get extraction status."""
        total_entities = sum(info.entity_count for info in self.tracking.values())
        total_rels = sum(info.relationship_count for info in self.tracking.values())
        return {
            "tracked_files": len(self.tracking),
            "total_entities": total_entities,
            "total_relationships": total_rels,
            "cache_stats": self.cache.get_stats(),
            "files": [
                {
                    "path": info.file_path,
                    "entities": info.entity_count,
                    "relationships": info.relationship_count,
                    "task_id": info.task_id,
                    "chapter": info.chapter,
                    "last_processed": info.last_processed,
                }
                for info in self.tracking.values()
            ],
        }

    def clear_tracking(self):
        """Clear all tracking information (but keep cache)."""
        self.tracking = {}
        if self.tracking_file.exists():
            self.tracking_file.unlink()

    def cleanup_orphan_cache(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Remove cache files that are not referenced in tracking.

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            Dict with cleanup statistics
        """
        # Get all valid content hashes from tracking
        valid_hashes = {info.content_hash for info in self.tracking.values()}

        # Find all cache files (excluding tracking file)
        cache_files = list(self.cache.cache_dir.glob("*.json"))
        tracking_filename = self.tracking_file.name

        orphans = []
        kept = []

        for cache_file in cache_files:
            if cache_file.name == tracking_filename:
                continue

            file_hash = cache_file.stem

            if file_hash not in valid_hashes:
                orphans.append(cache_file)
                if not dry_run:
                    cache_file.unlink()
            else:
                kept.append(cache_file)

        return {
            "orphans_found": len(orphans),
            "orphans_deleted": 0 if dry_run else len(orphans),
            "files_kept": len(kept),
            "dry_run": dry_run,
            "orphan_files": [str(f) for f in orphans],
        }

    def rebuild_tracking(
        self,
        data_dir: Path,
        pattern: str = "**/chapter*_dialogue.txt",
    ) -> Dict[str, Any]:
        """
        Rebuild tracking from existing cache files.

        This is faster than re-extracting when cache files exist but tracking
        was lost (e.g., due to race conditions or manual deletion).

        For each dialogue file:
        1. Compute content hash
        2. Check if cache file exists with that hash
        3. If yes, load cache and update tracking

        Args:
            data_dir: Root data directory to scan
            pattern: Glob pattern for dialogue files

        Returns:
            Dict with rebuild statistics
        """
        stats = {
            "files_scanned": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "already_tracked": 0,
        }

        dialogue_files = sorted(data_dir.glob(pattern))
        print(f"Scanning {len(dialogue_files)} files...")

        for file_path in dialogue_files:
            stats["files_scanned"] += 1
            file_key = str(file_path)

            # Skip if already tracked with same hash
            content = file_path.read_text(encoding="utf-8")
            content_hash = self._hash_content(content)

            if file_key in self.tracking:
                if self.tracking[file_key].content_hash == content_hash:
                    stats["already_tracked"] += 1
                    continue

            # Try to find cache
            cached = self.cache.get(content)
            if cached is None:
                stats["cache_misses"] += 1
                continue

            # Cache hit - rebuild tracking entry
            stats["cache_hits"] += 1
            metadata = self._parse_file_metadata(file_path)

            self.tracking[file_key] = KGFileTrackingInfo(
                file_path=file_key,
                content_hash=content_hash,
                last_processed=datetime.now().isoformat(),
                entity_count=len(cached.entities),
                relationship_count=len(cached.relationships),
                task_id=metadata["task_id"],
                chapter=metadata["chapter"],
            )

            print(f"  Restored: {file_path.name} ({len(cached.entities)} entities)")

        # Save tracking
        self._save_tracking()

        return stats


def write_kg_to_graph(
    extraction_results: List[Dict[str, Any]],
    dry_run: bool = False,
) -> Dict[str, int]:
    """
    Write extracted KG to the Neo4j graph.

    Args:
        extraction_results: List of extraction results from IncrementalKGExtractor
        dry_run: If True, don't actually write to graph

    Returns:
        Dict with statistics
    """
    from ..graph.builder import GraphBuilder

    stats = {
        "total_entities": 0,
        "total_relationships": 0,
        "entities_written": 0,
        "relationships_written": 0,
        "files_processed": 0,
    }

    if dry_run:
        for result in extraction_results:
            stats["total_entities"] += len(result["entities"])
            stats["total_relationships"] += len(result["relationships"])
            stats["files_processed"] += 1
        return stats

    with GraphBuilder() as builder:
        builder.setup_schema()

        for result in extraction_results:
            entities = result["entities"]
            relationships = result["relationships"]
            chapter = result["chapter"]
            task_id = result["task_id"]

            # Convert Pydantic models to dicts
            entity_dicts = [e.model_dump() for e in entities]
            rel_dicts = [r.model_dump() for r in relationships]

            # Write entities
            for entity in entity_dicts:
                entity_type = entity.get("entity_type", "Character")
                if entity_type == "Character":
                    builder.create_character_simple(
                        name=entity["name"],
                        task_id=task_id,
                        chapter=chapter,
                    )
                    stats["entities_written"] += 1
                elif entity_type == "Organization":
                    builder.create_organization(
                        name=entity["name"],
                        task_id=task_id,
                    )
                    stats["entities_written"] += 1

            # Write relationships
            for rel in rel_dicts:
                success = builder.create_relationship(
                    source=rel["source"],
                    target=rel["target"],
                    relation_type=rel["relation_type"],
                    chapter=chapter,
                    task_id=task_id,
                    description=rel.get("description"),
                    evidence=rel.get("evidence"),
                )
                if success:
                    stats["relationships_written"] += 1

            stats["total_entities"] += len(entities)
            stats["total_relationships"] += len(relationships)
            stats["files_processed"] += 1

    return stats


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    print("Incremental KG Extractor")
    print("=" * 60)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m src.ingestion.incremental_kg_extractor <folder>")
        print("  python -m src.ingestion.incremental_kg_extractor Data/Archon/1608")
        print("  python -m src.ingestion.incremental_kg_extractor Data/Archon/1608 --write")
        print("  python -m src.ingestion.incremental_kg_extractor --cleanup")
        print("  python -m src.ingestion.incremental_kg_extractor --cleanup --dry-run")
        print("  python -m src.ingestion.incremental_kg_extractor --rebuild Data/")
        print("  python -m src.ingestion.incremental_kg_extractor --status")
        sys.exit(1)

    # Initialize extractor
    extractor = IncrementalKGExtractor()

    # Handle special commands
    if "--rebuild" in sys.argv:
        # Find the data directory argument
        data_dir = None
        for arg in sys.argv[1:]:
            if not arg.startswith("--"):
                data_dir = Path(arg)
                break
        if data_dir is None:
            data_dir = Path("Data/")

        print(f"\nRebuilding tracking from cache for: {data_dir}")
        stats = extractor.rebuild_tracking(data_dir)
        print(f"\n{'='*60}")
        print(f"REBUILD COMPLETE")
        print(f"{'='*60}")
        print(f"Files scanned: {stats['files_scanned']}")
        print(f"Already tracked: {stats['already_tracked']}")
        print(f"Cache hits (restored): {stats['cache_hits']}")
        print(f"Cache misses (need extraction): {stats['cache_misses']}")
        sys.exit(0)

    if "--cleanup" in sys.argv:
        dry_run = "--dry-run" in sys.argv
        print(f"\nCleaning orphan cache files (dry_run={dry_run})...")
        result = extractor.cleanup_orphan_cache(dry_run=dry_run)
        print(f"  Tracked files: {len(extractor.tracking)}")
        print(f"  Cache files kept: {result['files_kept']}")
        print(f"  Orphans found: {result['orphans_found']}")
        if dry_run:
            print(f"  (Dry run - no files deleted)")
            if result['orphan_files']:
                print(f"\n  Would delete:")
                for f in result['orphan_files']:
                    print(f"    {f}")
        else:
            print(f"  Orphans deleted: {result['orphans_deleted']}")
        sys.exit(0)

    if "--status" in sys.argv:
        status = extractor.get_status()
        print(f"\nTracked files: {status['tracked_files']}")
        print(f"Total entities: {status['total_entities']}")
        print(f"Total relationships: {status['total_relationships']}")
        print(f"Cache stats: {status['cache_stats']}")
        print(f"\nFiles:")
        for f in status['files']:
            print(f"  {f['path']}: {f['entities']} entities, {f['relationships']} rels (chapter {f['chapter']})")
        sys.exit(0)

    folder = Path(sys.argv[1])
    write_to_graph = "--write" in sys.argv

    if not folder.exists():
        print(f"Error: Folder not found: {folder}")
        sys.exit(1)

    # Extract KG
    print(f"\nExtracting KG from: {folder}")
    results = extractor.extract_folder(folder)

    # Print summary
    total_entities = sum(len(r["entities"]) for r in results)
    total_rels = sum(len(r["relationships"]) for r in results)
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Files processed: {len(results)}")
    print(f"Total entities: {total_entities}")
    print(f"Total relationships: {total_rels}")

    # Count entity types
    entity_types: Dict[str, int] = {}
    for result in results:
        for entity in result["entities"]:
            t = entity.entity_type
            entity_types[t] = entity_types.get(t, 0) + 1

    print(f"\nEntity types:")
    for t, count in sorted(entity_types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")

    # Count relationship types
    rel_types: Dict[str, int] = {}
    for result in results:
        for rel in result["relationships"]:
            t = rel.relation_type
            rel_types[t] = rel_types.get(t, 0) + 1

    print(f"\nRelationship types:")
    for t, count in sorted(rel_types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")

    # Print sample
    print(f"\nSample entities:")
    for result in results[:1]:
        print(f"\n  File: {result['file_path']}")
        for entity in result["entities"][:5]:
            role_str = f" ({entity.role})" if entity.role else ""
            print(f"    [{entity.entity_type}] {entity.name}{role_str}")

    # Write to graph if requested
    if write_to_graph:
        print(f"\n{'='*60}")
        print("Writing KG to Neo4j graph...")
        stats = write_kg_to_graph(results)
        print(f"Entities written: {stats['entities_written']}")
        print(f"Relationships written: {stats['relationships_written']}")
    else:
        print(f"\nTo write KG to graph, run with --write flag")
