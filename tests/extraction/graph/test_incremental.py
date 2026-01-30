"""
Tests for Incremental Knowledge Graph Extraction.

These tests verify incremental extraction functionality WITHOUT requiring LLM access.
They test:
1. KGMerger entity deduplication and alias normalization
2. FileTrackingInfo dataclass
3. KGSnapshotManager save/load/list operations
4. IncrementalKGExtractor file tracking (without actual LLM calls)

Note: Tests that require LLM are in test_llm_kg_extractor.py
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

# Import the modules to test - add src and src/ingestion to path
import sys
src_path = str(Path(__file__).parent.parent.parent.parent / "src")
ingestion_path = str(Path(__file__).parent.parent.parent.parent / "src" / "ingestion")

# Add both paths to ensure imports work
for path in [src_path, ingestion_path]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import directly from module files (bypassing __init__.py)
from llm_kg_extractor import (
    ExtractedEntity,
    ExtractedRelationship,
    KnowledgeGraphOutput,
)
from incremental_extractor import (
    FileTrackingInfo,
    KGMerger,
    IncrementalKGExtractor,
)
from kg_snapshot import KGSnapshotManager


# =============================================================================
# KGMerger Tests
# =============================================================================

class TestKGMerger:
    """Test KG merging and entity deduplication."""

    def test_merge_empty_list(self):
        """Test merging empty list returns empty KG."""
        merger = KGMerger()
        result = merger.merge([])
        assert len(result.entities) == 0
        assert len(result.relationships) == 0

    def test_merge_single_kg(self):
        """Test merging single KG returns same entities."""
        merger = KGMerger()
        kg = KnowledgeGraphOutput(
            entities=[
                ExtractedEntity(name="派蒙", entity_type="Character"),
                ExtractedEntity(name="恰斯卡", entity_type="Character"),
            ],
            relationships=[
                ExtractedRelationship(source="派蒙", target="恰斯卡", relation_type="KNOWS"),
            ]
        )
        result = merger.merge([kg])
        assert len(result.entities) == 2
        assert len(result.relationships) == 1

    def test_alias_normalization(self):
        """Test that aliases are normalized to canonical names."""
        merger = KGMerger()

        # 杜麦尼 should be normalized to 旅行者
        kg = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="杜麦尼", entity_type="Character")],
            relationships=[]
        )
        result = merger.merge([kg])

        names = result.get_entity_names()
        assert "旅行者" in names
        assert "杜麦尼" not in names

        # Original name should be stored as alias
        traveler = [e for e in result.entities if e.name == "旅行者"][0]
        assert "杜麦尼" in traveler.aliases

    def test_merge_deduplication_by_name(self):
        """Test that entities with same name are deduplicated."""
        merger = KGMerger()

        kg1 = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="派蒙", entity_type="Character")],
            relationships=[]
        )
        kg2 = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="派蒙", entity_type="Character")],
            relationships=[]
        )

        result = merger.merge([kg1, kg2])
        assert len(result.entities) == 1
        assert result.entities[0].name == "派蒙"

    def test_merge_deduplication_by_alias(self):
        """Test that entities with aliased names are deduplicated."""
        merger = KGMerger()

        kg1 = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="杜麦尼", entity_type="Character")],
            relationships=[]
        )
        kg2 = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="旅行者", entity_type="Character")],
            relationships=[]
        )

        result = merger.merge([kg1, kg2])
        assert len(result.entities) == 1
        assert result.entities[0].name == "旅行者"
        assert "杜麦尼" in result.entities[0].aliases

    def test_merge_preserves_roles(self):
        """Test that roles are preserved during merge."""
        merger = KGMerger()

        kg1 = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="伊法", entity_type="Character")],
            relationships=[]
        )
        kg2 = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="伊法", entity_type="Character", role="医生")],
            relationships=[]
        )

        result = merger.merge([kg1, kg2])
        assert len(result.entities) == 1
        assert result.entities[0].role == "医生"

    def test_merge_combines_aliases(self):
        """Test that aliases are combined during merge."""
        merger = KGMerger()

        kg1 = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="派蒙", entity_type="Character", aliases=["飞行高手"])],
            relationships=[]
        )
        kg2 = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="派蒙", entity_type="Character", aliases=["白色飞行物"])],
            relationships=[]
        )

        result = merger.merge([kg1, kg2])
        paimon = result.entities[0]
        assert "飞行高手" in paimon.aliases
        assert "白色飞行物" in paimon.aliases

    def test_relationship_deduplication(self):
        """Test that duplicate relationships are removed."""
        merger = KGMerger()

        kg1 = KnowledgeGraphOutput(
            entities=[],
            relationships=[
                ExtractedRelationship(source="派蒙", target="恰斯卡", relation_type="KNOWS"),
            ]
        )
        kg2 = KnowledgeGraphOutput(
            entities=[],
            relationships=[
                ExtractedRelationship(source="派蒙", target="恰斯卡", relation_type="KNOWS"),
            ]
        )

        result = merger.merge([kg1, kg2])
        assert len(result.relationships) == 1

    def test_relationship_alias_normalization(self):
        """Test that relationship sources/targets are normalized."""
        merger = KGMerger()

        kg = KnowledgeGraphOutput(
            entities=[],
            relationships=[
                ExtractedRelationship(source="杜麦尼", target="派蒙", relation_type="KNOWS"),
            ]
        )

        result = merger.merge([kg])
        assert result.relationships[0].source == "旅行者"

    def test_custom_alias_map(self):
        """Test using custom alias map."""
        custom_map = {"小派蒙": "派蒙"}
        merger = KGMerger(alias_map=custom_map)

        kg = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="小派蒙", entity_type="Character")],
            relationships=[]
        )

        result = merger.merge([kg])
        assert "派蒙" in result.get_entity_names()
        assert "小派蒙" not in result.get_entity_names()

    def test_add_alias(self):
        """Test dynamically adding aliases."""
        merger = KGMerger()
        merger.add_alias("应急食品", "派蒙")

        kg = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="应急食品", entity_type="Character")],
            relationships=[]
        )

        result = merger.merge([kg])
        assert "派蒙" in result.get_entity_names()


# =============================================================================
# FileTrackingInfo Tests
# =============================================================================

class TestFileTrackingInfo:
    """Test FileTrackingInfo dataclass."""

    def test_creation(self):
        """Test creating FileTrackingInfo."""
        info = FileTrackingInfo(
            file_path="/path/to/file.txt",
            content_hash="abc123",
            last_processed="2024-01-15T10:30:00",
            entity_count=5,
            relationship_count=3
        )
        assert info.file_path == "/path/to/file.txt"
        assert info.content_hash == "abc123"
        assert info.entity_count == 5
        assert info.relationship_count == 3

    def test_to_dict(self):
        """Test converting to dict."""
        info = FileTrackingInfo(
            file_path="/path/to/file.txt",
            content_hash="abc123",
            last_processed="2024-01-15T10:30:00",
            entity_count=5,
            relationship_count=3
        )
        d = info.__dict__
        assert d["file_path"] == "/path/to/file.txt"
        assert "content_hash" in d


# =============================================================================
# KGSnapshotManager Tests
# =============================================================================

class TestKGSnapshotManager:
    """Test KG snapshot management."""

    @pytest.fixture
    def temp_snapshot_dir(self, tmp_path):
        """Create a temporary snapshot directory."""
        return str(tmp_path / "snapshots")

    @pytest.fixture
    def manager(self, temp_snapshot_dir):
        """Create a snapshot manager with temp directory."""
        return KGSnapshotManager(snapshot_dir=temp_snapshot_dir)

    @pytest.fixture
    def sample_kg(self):
        """Create a sample KG for testing."""
        return KnowledgeGraphOutput(
            entities=[
                ExtractedEntity(name="派蒙", entity_type="Character"),
                ExtractedEntity(name="恰斯卡", entity_type="Character"),
                ExtractedEntity(name="花羽会", entity_type="Organization"),
            ],
            relationships=[
                ExtractedRelationship(source="派蒙", target="恰斯卡", relation_type="KNOWS"),
            ]
        )

    def test_save_snapshot(self, manager, sample_kg):
        """Test saving a snapshot."""
        path = manager.save(sample_kg, name="test")
        assert path.exists()
        assert "test_" in path.name

    def test_save_snapshot_without_name(self, manager, sample_kg):
        """Test saving snapshot without name."""
        path = manager.save(sample_kg)
        assert path.exists()
        assert "snapshot_" in path.name

    def test_load_snapshot(self, manager, sample_kg):
        """Test loading a snapshot."""
        path = manager.save(sample_kg, name="test")
        loaded = manager.load(path)

        assert len(loaded.entities) == len(sample_kg.entities)
        assert len(loaded.relationships) == len(sample_kg.relationships)

    def test_load_with_metadata(self, manager, sample_kg):
        """Test loading snapshot with metadata."""
        path = manager.save(sample_kg, name="test", metadata={"source": "unit_test"})
        data = manager.load_with_metadata(path)

        assert data["name"] == "test"
        assert data["metadata"]["source"] == "unit_test"
        assert isinstance(data["kg"], KnowledgeGraphOutput)

    def test_list_snapshots(self, manager, sample_kg):
        """Test listing snapshots."""
        manager.save(sample_kg, name="snapshot1")
        manager.save(sample_kg, name="snapshot2")

        snapshots = manager.list_snapshots()
        assert len(snapshots) == 2
        # Should be sorted by creation time (newest first)
        assert snapshots[0]["name"] == "snapshot2"

    def test_get_latest(self, manager, sample_kg):
        """Test getting latest snapshot."""
        manager.save(sample_kg, name="old")
        manager.save(sample_kg, name="new")

        latest = manager.get_latest()
        assert latest is not None
        # Both snapshots have same content, so just check it loaded

    def test_get_latest_path(self, manager, sample_kg):
        """Test getting latest snapshot path."""
        manager.save(sample_kg, name="test1")
        path2 = manager.save(sample_kg, name="test2")

        latest_path = manager.get_latest_path()
        assert latest_path == path2

    def test_get_latest_empty(self, manager):
        """Test getting latest when no snapshots exist."""
        latest = manager.get_latest()
        assert latest is None

    def test_get_by_name(self, manager, sample_kg):
        """Test getting snapshot by name."""
        manager.save(sample_kg, name="target")
        manager.save(sample_kg, name="other")

        result = manager.get_by_name("target")
        assert result is not None

    def test_get_by_name_not_found(self, manager, sample_kg):
        """Test getting non-existent snapshot by name."""
        manager.save(sample_kg, name="something")
        result = manager.get_by_name("nonexistent")
        assert result is None

    def test_delete_snapshot(self, manager, sample_kg):
        """Test deleting a snapshot."""
        path = manager.save(sample_kg, name="to_delete")
        assert path.exists()

        result = manager.delete(path)
        assert result is True
        assert not path.exists()

    def test_delete_nonexistent(self, manager, tmp_path):
        """Test deleting non-existent snapshot."""
        result = manager.delete(tmp_path / "nonexistent.json")
        assert result is False

    def test_clear_all(self, manager, sample_kg):
        """Test clearing all snapshots."""
        manager.save(sample_kg, name="snap1")
        manager.save(sample_kg, name="snap2")

        assert len(manager.list_snapshots()) == 2

        manager.clear_all()
        assert len(manager.list_snapshots()) == 0

    def test_compare_snapshots(self, manager):
        """Test comparing two snapshots."""
        kg1 = KnowledgeGraphOutput(
            entities=[
                ExtractedEntity(name="派蒙", entity_type="Character"),
                ExtractedEntity(name="恰斯卡", entity_type="Character"),
            ],
            relationships=[]
        )
        kg2 = KnowledgeGraphOutput(
            entities=[
                ExtractedEntity(name="派蒙", entity_type="Character"),
                ExtractedEntity(name="伊法", entity_type="Character"),
            ],
            relationships=[]
        )

        path1 = manager.save(kg1, name="version1")
        path2 = manager.save(kg2, name="version2")

        comparison = manager.compare(path1, path2)

        assert "恰斯卡" in comparison["entities"]["only_in_1"]
        assert "伊法" in comparison["entities"]["only_in_2"]
        assert "派蒙" in comparison["entities"]["in_both"]

    def test_snapshot_stats(self, manager, sample_kg):
        """Test that snapshot stats are calculated correctly."""
        path = manager.save(sample_kg, name="test")
        snapshots = manager.list_snapshots()

        snap = snapshots[0]
        assert snap["entities"] == 3
        assert snap["relationships"] == 1
        assert snap["characters"] == 2
        assert snap["organizations"] == 1


# =============================================================================
# IncrementalKGExtractor Tests (No LLM)
# =============================================================================

class TestIncrementalKGExtractorNoLLM:
    """Test IncrementalKGExtractor without requiring LLM."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create a temporary cache directory."""
        return str(tmp_path / "cache")

    @pytest.fixture
    def extractor(self, temp_cache_dir):
        """Create extractor with temp cache."""
        return IncrementalKGExtractor(cache_dir=temp_cache_dir)

    def test_hash_content_deterministic(self, extractor):
        """Test that hash is deterministic."""
        text = "测试文本"
        hash1 = extractor._hash_content(text)
        hash2 = extractor._hash_content(text)
        assert hash1 == hash2

    def test_hash_content_different(self, extractor):
        """Test that different content has different hash."""
        hash1 = extractor._hash_content("文本1")
        hash2 = extractor._hash_content("文本2")
        assert hash1 != hash2

    def test_tracking_persistence(self, temp_cache_dir, tmp_path):
        """Test that tracking data persists across instances."""
        # Create first extractor and add tracking
        ext1 = IncrementalKGExtractor(cache_dir=temp_cache_dir)
        ext1.tracking["test_file"] = FileTrackingInfo(
            file_path="test_file",
            content_hash="abc123",
            last_processed="2024-01-15T10:00:00",
            entity_count=5,
            relationship_count=3
        )
        ext1._save_tracking()

        # Create second extractor and verify tracking loaded
        ext2 = IncrementalKGExtractor(cache_dir=temp_cache_dir)
        assert "test_file" in ext2.tracking
        assert ext2.tracking["test_file"].content_hash == "abc123"

    def test_get_status(self, extractor):
        """Test getting extraction status."""
        status = extractor.get_status()
        assert "tracked_files" in status
        assert "cache_stats" in status
        assert "files" in status

    def test_clear_tracking(self, extractor):
        """Test clearing tracking."""
        extractor.tracking["test"] = FileTrackingInfo(
            file_path="test",
            content_hash="abc",
            last_processed="2024-01-15",
            entity_count=1,
            relationship_count=0
        )
        extractor._save_tracking()

        extractor.clear_tracking()
        assert len(extractor.tracking) == 0

    def test_get_changed_files_new_directory(self, extractor, tmp_path):
        """Test detecting new files in empty tracking."""
        # Create test files
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "chapter0_dialogue.txt").write_text("dialogue content")
        (data_dir / "chapter1_dialogue.txt").write_text("more dialogue")

        changed = extractor.get_changed_files(data_dir)
        assert len(changed) == 2

    def test_get_changed_files_with_tracking(self, extractor, tmp_path):
        """Test detecting changed files with existing tracking."""
        # Create test file
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        file_path = data_dir / "chapter0_dialogue.txt"
        file_path.write_text("original content")

        # Add to tracking with current hash
        content_hash = extractor._hash_file(file_path)
        extractor.tracking[str(file_path)] = FileTrackingInfo(
            file_path=str(file_path),
            content_hash=content_hash,
            last_processed="2024-01-15",
            entity_count=1,
            relationship_count=0
        )

        # File unchanged - should not be in changed list
        changed = extractor.get_changed_files(data_dir)
        assert len(changed) == 0

        # Modify file
        file_path.write_text("modified content")

        # Now should detect change
        changed = extractor.get_changed_files(data_dir)
        assert len(changed) == 1

    def test_merger_integration(self, extractor):
        """Test that extractor has merger configured."""
        assert extractor.merger is not None
        assert isinstance(extractor.merger, KGMerger)

    def test_cache_integration(self, extractor):
        """Test that extractor has cache configured."""
        assert extractor.cache is not None


# =============================================================================
# Integration Tests (Still No LLM)
# =============================================================================

class TestIntegration:
    """Integration tests that don't require LLM."""

    def test_merger_and_snapshot_workflow(self, tmp_path):
        """Test complete workflow: merge KGs then save snapshot."""
        # Create KGs
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

        # Merge
        merger = KGMerger()
        merged = merger.merge([kg1, kg2])

        # Verify merge results
        assert len(merged.entities) == 3  # 旅行者 (merged), 派蒙, 恰斯卡
        assert "旅行者" in merged.get_entity_names()
        assert "杜麦尼" not in merged.get_entity_names()

        # Save snapshot
        manager = KGSnapshotManager(snapshot_dir=str(tmp_path / "snapshots"))
        path = manager.save(merged, name="merged_test")

        # Load and verify
        loaded = manager.load(path)
        assert loaded.get_entity_names() == merged.get_entity_names()

    def test_full_alias_chain(self, tmp_path):
        """Test merging entities that should all resolve to same canonical name."""
        merger = KGMerger()

        # Multiple representations of 旅行者
        kgs = [
            KnowledgeGraphOutput(
                entities=[ExtractedEntity(name="杜麦尼", entity_type="Character")],
                relationships=[]
            ),
            KnowledgeGraphOutput(
                entities=[ExtractedEntity(name="玩家", entity_type="Character")],
                relationships=[]
            ),
            KnowledgeGraphOutput(
                entities=[ExtractedEntity(name="旅行者", entity_type="Character")],
                relationships=[]
            ),
        ]

        merged = merger.merge(kgs)

        # Should have exactly one entity
        assert len(merged.entities) == 1
        assert merged.entities[0].name == "旅行者"
        assert "杜麦尼" in merged.entities[0].aliases
        assert "玩家" in merged.entities[0].aliases
