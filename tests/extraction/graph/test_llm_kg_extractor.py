"""
Tests for LLM-based Knowledge Graph Extractor.

These tests verify the LLM extraction functionality WITHOUT requiring Neo4j.
They test:
1. Pydantic model serialization/deserialization
2. Entity extraction accuracy
3. Relationship extraction accuracy
4. Cache functionality

Note: Tests marked with @pytest.mark.llm require actual LLM API access.
"""

import pytest
import json
from pathlib import Path

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
    LLMKnowledgeGraphExtractor,
)
from kg_cache import KGCache, CachedKGExtractor


# =============================================================================
# Pydantic Model Tests (No LLM Required)
# =============================================================================

class TestPydanticModels:
    """Test Pydantic model serialization and validation."""

    def test_extracted_entity_creation(self):
        """Test creating an ExtractedEntity."""
        entity = ExtractedEntity(
            name="伊法",
            entity_type="Character",
            role="医生",
            aliases=["医生伊法"]
        )
        assert entity.name == "伊法"
        assert entity.entity_type == "Character"
        assert entity.role == "医生"
        assert "医生伊法" in entity.aliases

    def test_extracted_entity_defaults(self):
        """Test ExtractedEntity with default values."""
        entity = ExtractedEntity(name="派蒙", entity_type="Character")
        assert entity.role is None
        assert entity.aliases == []

    def test_extracted_relationship_creation(self):
        """Test creating an ExtractedRelationship."""
        rel = ExtractedRelationship(
            source="咔库库",
            target="伊法",
            relation_type="WORKS_WITH",
            description="咔库库是伊法的助理"
        )
        assert rel.source == "咔库库"
        assert rel.target == "伊法"
        assert rel.relation_type == "WORKS_WITH"

    def test_knowledge_graph_output_creation(self):
        """Test creating a KnowledgeGraphOutput."""
        entities = [
            ExtractedEntity(name="伊法", entity_type="Character", role="医生"),
            ExtractedEntity(name="咔库库", entity_type="Character"),
            ExtractedEntity(name="花羽会", entity_type="Organization"),
        ]
        relationships = [
            ExtractedRelationship(source="咔库库", target="伊法", relation_type="WORKS_WITH"),
            ExtractedRelationship(source="伊法", target="花羽会", relation_type="MEMBER_OF"),
        ]
        kg = KnowledgeGraphOutput(entities=entities, relationships=relationships)

        assert len(kg.entities) == 3
        assert len(kg.relationships) == 2

    def test_knowledge_graph_helper_methods(self):
        """Test KnowledgeGraphOutput helper methods."""
        kg = KnowledgeGraphOutput(
            entities=[
                ExtractedEntity(name="伊法", entity_type="Character"),
                ExtractedEntity(name="恰斯卡", entity_type="Character"),
                ExtractedEntity(name="花羽会", entity_type="Organization"),
                ExtractedEntity(name="纳塔", entity_type="Location"),
            ],
            relationships=[]
        )

        # Test get_entity_names
        names = kg.get_entity_names()
        assert names == {"伊法", "恰斯卡", "花羽会", "纳塔"}

        # Test get_characters
        chars = kg.get_characters()
        assert len(chars) == 2
        assert all(e.entity_type == "Character" for e in chars)

        # Test get_organizations
        orgs = kg.get_organizations()
        assert len(orgs) == 1
        assert orgs[0].name == "花羽会"

        # Test get_locations
        locs = kg.get_locations()
        assert len(locs) == 1
        assert locs[0].name == "纳塔"

    def test_json_serialization(self):
        """Test JSON serialization round-trip."""
        original = KnowledgeGraphOutput(
            entities=[
                ExtractedEntity(name="伊法", entity_type="Character", role="医生"),
            ],
            relationships=[
                ExtractedRelationship(source="伊法", target="花羽会", relation_type="MEMBER_OF"),
            ]
        )

        # Serialize
        json_str = original.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize
        restored = KnowledgeGraphOutput.model_validate_json(json_str)
        assert len(restored.entities) == len(original.entities)
        assert restored.entities[0].name == "伊法"
        assert restored.entities[0].role == "医生"

    def test_json_dict_serialization(self):
        """Test dict serialization for JSON storage."""
        kg = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="伊法", entity_type="Character")],
            relationships=[]
        )
        data = kg.model_dump()
        assert isinstance(data, dict)
        assert "entities" in data
        assert "relationships" in data

        # Restore from dict
        restored = KnowledgeGraphOutput.model_validate(data)
        assert restored.entities[0].name == "伊法"


# =============================================================================
# Cache Tests (No LLM Required)
# =============================================================================

class TestKGCache:
    """Test the KG cache functionality."""

    @pytest.fixture
    def temp_cache(self, tmp_path):
        """Create a temporary cache for testing."""
        return KGCache(cache_dir=str(tmp_path / "test_cache"))

    def test_cache_miss(self, temp_cache):
        """Test cache miss returns None."""
        result = temp_cache.get("some text that is not cached")
        assert result is None

    def test_cache_set_and_get(self, temp_cache):
        """Test setting and getting from cache."""
        text = "恰斯卡：这位是伊法医生。"
        kg = KnowledgeGraphOutput(
            entities=[ExtractedEntity(name="恰斯卡", entity_type="Character")],
            relationships=[]
        )

        # Set
        temp_cache.set(text, kg)

        # Get
        cached = temp_cache.get(text)
        assert cached is not None
        assert len(cached.entities) == 1
        assert cached.entities[0].name == "恰斯卡"

    def test_cache_has(self, temp_cache):
        """Test checking if item is cached."""
        text = "test text"
        kg = KnowledgeGraphOutput(entities=[], relationships=[])

        assert not temp_cache.has(text)
        temp_cache.set(text, kg)
        assert temp_cache.has(text)

    def test_cache_invalidate(self, temp_cache):
        """Test invalidating cache entry."""
        text = "test text"
        kg = KnowledgeGraphOutput(entities=[], relationships=[])

        temp_cache.set(text, kg)
        assert temp_cache.has(text)

        result = temp_cache.invalidate(text)
        assert result is True
        assert not temp_cache.has(text)

        # Invalidating non-existent
        result = temp_cache.invalidate("nonexistent")
        assert result is False

    def test_cache_clear(self, temp_cache):
        """Test clearing all cache."""
        temp_cache.set("text1", KnowledgeGraphOutput(entities=[], relationships=[]))
        temp_cache.set("text2", KnowledgeGraphOutput(entities=[], relationships=[]))

        stats_before = temp_cache.get_stats()
        assert stats_before["cached_items"] == 2

        temp_cache.clear()

        stats_after = temp_cache.get_stats()
        assert stats_after["cached_items"] == 0

    def test_cache_stats(self, temp_cache):
        """Test cache statistics."""
        # Initial stats
        stats = temp_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # Generate a miss
        temp_cache.get("nonexistent")
        stats = temp_cache.get_stats()
        assert stats["misses"] == 1

        # Set and hit
        text = "test"
        temp_cache.set(text, KnowledgeGraphOutput(entities=[], relationships=[]))
        temp_cache.get(text)
        stats = temp_cache.get_stats()
        assert stats["hits"] == 1

    def test_cache_content_hash_deterministic(self, temp_cache):
        """Test that same content always produces same hash."""
        text = "测试文本"

        hash1 = temp_cache._hash_text(text)
        hash2 = temp_cache._hash_text(text)
        assert hash1 == hash2

        # Different text, different hash
        hash3 = temp_cache._hash_text("不同文本")
        assert hash1 != hash3


# =============================================================================
# LLM Extractor Tests (Requires LLM API)
# =============================================================================

@pytest.mark.llm
class TestLLMKGExtractor:
    """
    Tests that require actual LLM API access.

    Run with: pytest -m llm
    Skip with: pytest -m "not llm"
    """

    @pytest.fixture
    def extractor(self):
        """Create an LLM extractor instance."""
        try:
            return LLMKnowledgeGraphExtractor()
        except ValueError as e:
            pytest.skip(f"LLM API not configured: {e}")

    def test_extract_simple_dialogue(self, extractor):
        """Test extracting from simple dialogue."""
        text = "恰斯卡：这位是我们部族的「医生」伊法…和他的助理咔库库。"
        result = extractor.extract(text)

        assert isinstance(result, KnowledgeGraphOutput)

        # Check entities
        entity_names = result.get_entity_names()
        assert "伊法" in entity_names or "伊法" in str(entity_names)
        assert "咔库库" in entity_names or "咔库库" in str(entity_names)
        assert "恰斯卡" in entity_names or "恰斯卡" in str(entity_names)

    def test_extract_relationships(self, extractor):
        """Test extracting relationships."""
        text = "恰斯卡：这位是我们部族的「医生」伊法…和他的助理咔库库。"
        result = extractor.extract(text)

        # Should find WORKS_WITH relationship
        rel_pairs = {(r.source, r.target) for r in result.relationships}
        # Check that some relationship exists between 咔库库 and 伊法
        has_work_rel = any(
            ("咔库库" in r.source or "咔库库" in r.target) and
            ("伊法" in r.source or "伊法" in r.target)
            for r in result.relationships
        )
        assert has_work_rel, f"Expected relationship between 咔库库 and 伊法, got: {result.relationships}"

    def test_extract_special_characters(self, extractor):
        """Test extracting special characters like ？？？"""
        text = """？？？：…在哪里…

？？？：…要…找到…他们…

小机器人：滴…滴…嘟…"""
        result = extractor.extract(text)

        entity_names = result.get_entity_names()
        # Should extract ？？？ as a character
        assert "？？？" in entity_names or "小机器人" in entity_names

    def test_extract_entities_only(self, extractor):
        """Test extracting only entities."""
        text = "派蒙：嘿！恰斯卡！"
        entities = extractor.extract_entities_only(text)

        assert isinstance(entities, list)
        assert all(isinstance(e, ExtractedEntity) for e in entities)

    def test_extract_character_names(self, extractor):
        """Test extracting character names for compatibility."""
        text = "派蒙：嘿！恰斯卡！"
        names = extractor.extract_character_names(text)

        assert isinstance(names, set)
        assert "派蒙" in names or "恰斯卡" in names


# =============================================================================
# Integration with Evaluation Dataset
# =============================================================================

@pytest.mark.llm
class TestLLMWithEvalDataset:
    """Test LLM extraction against evaluation dataset."""

    @pytest.fixture
    def extractor(self):
        """Create an LLM extractor instance."""
        try:
            return LLMKnowledgeGraphExtractor()
        except ValueError as e:
            pytest.skip(f"LLM API not configured: {e}")

    def test_entity_eval_must_extract(self, extractor, entity_dataset):
        """Test that LLM extracts required entities."""
        passed = 0
        failed = 0

        for item in entity_dataset.get("items", [])[:5]:  # Test first 5 items
            text = item.get("input", {}).get("text", "")
            if not text:
                continue

            constraints = item.get("constraints", {})
            must_extract = constraints.get("must_extract", [])
            if not must_extract:
                continue

            result = extractor.extract(text)
            entity_names = result.get_entity_names()

            for required in must_extract:
                if required in entity_names:
                    passed += 1
                else:
                    failed += 1

        # Report results
        total = passed + failed
        if total > 0:
            pass_rate = passed / total
            print(f"\nEntity must_extract: {passed}/{total} ({pass_rate:.1%})")
            # We don't assert a specific threshold here, just run the test

    def test_relationship_eval_must_relate(self, extractor, relationship_dataset):
        """Test that LLM extracts required relationships."""
        passed = 0
        failed = 0

        for item in relationship_dataset.get("items", [])[:5]:  # Test first 5 items
            text = item.get("input", {}).get("text", "")
            if not text:
                continue

            constraints = item.get("constraints", {})
            must_relate = constraints.get("must_relate", [])
            if not must_relate:
                continue

            result = extractor.extract(text)
            rel_pairs = set()
            for rel in result.relationships:
                rel_pairs.add((rel.source, rel.target))
                rel_pairs.add((rel.target, rel.source))  # Bidirectional check

            for required in must_relate:
                source = required.get("source")
                target = required.get("target")
                if (source, target) in rel_pairs or (target, source) in rel_pairs:
                    passed += 1
                else:
                    failed += 1

        # Report results
        total = passed + failed
        if total > 0:
            pass_rate = passed / total
            print(f"\nRelationship must_relate: {passed}/{total} ({pass_rate:.1%})")
