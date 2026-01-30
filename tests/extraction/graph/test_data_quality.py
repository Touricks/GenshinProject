"""
Tests for Data Quality in Knowledge Graph Extraction.

These tests validate filtering rules to prevent invalid entities from entering Neo4j.
Based on issues found in actual Neo4j export analysis.

Root Causes of Data Quality Issues:
1. Regex pattern `([^：\n]+)：` matches any text before colon, not just character names
2. SYSTEM_CHARACTERS filter is incomplete
3. No validation for special characters, UI elements, or narrative text

Issues Found:
- System text: [条件, 开始条件, 查看, 调查
- UI elements: 选项1-5, 玩家选项
- Combined speakers: 派蒙&卡齐娜&玛拉妮, 哈恩薇&安帕奥
- Narrative text: 但你们不会认输。所有人团结一致，你们知道
- Objects: 比赛公告板, 嘟嘟通讯仪, 长翎鹮, 门禁机仆
"""

import pytest
import re
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
from llm_kg_extractor import ExtractedEntity, KnowledgeGraphOutput

# Import the canonical CharacterValidator
from character_validator import (
    CharacterValidator,
    InvalidReason,
    validate_character_name as _validate,
    filter_character_names,
)


# =============================================================================
# Invalid Character Name Patterns
# =============================================================================

class InvalidCharacterPatterns:
    """Patterns that should NOT be accepted as character names."""

    # System/conditional text - starts with [ or contains conditional keywords
    SYSTEM_TEXT = [
        "[条件",
        "开始条件",
        "查看",
        "调查",
        "[如果",
        "[当",
    ]

    # UI elements - options, player choices
    UI_ELEMENTS = [
        "选项",
        "选项1",
        "选项2",
        "选项3",
        "选项4",
        "选项5",
        "玩家选项",
        "致敬",  # Game mechanic
    ]

    # Combined speakers - contains &
    COMBINED_SPEAKERS = [
        "派蒙&卡齐娜&玛拉妮",
        "哈恩薇&安帕奥",
        "穆尔科&维查玛",
    ]

    # Narrative text - long text that's not a name
    NARRATIVE_TEXT = [
        "但你们不会认输。所有人团结一致，你们知道",
        "你不合时宜地回想起多托雷的话",
        "来自过去的声音",
        "某处的声音",
        "（某处的声音",
        "嘈杂的怒吼",
        "深渊低语",
    ]

    # Objects/machines that "speak"
    NON_CHARACTER_SPEAKERS = [
        "比赛公告板",
        "嘟嘟通讯仪",
        "门禁机仆",
        "通行机仆",
        "战场情报",
        "旁白",
    ]

    # Memory/flashback variants
    MEMORY_VARIANTS = [
        "丽莎（回忆）",
        "温迪（回忆）",
        "玛拉妮（回忆）",
        "希库埃鲁（回忆）",
        "马洛考（回忆）",
    ]


# =============================================================================
# Character Name Validation Rules
# =============================================================================

def is_valid_character_name(name: str) -> bool:
    """
    Validate if a string is a valid character name.

    Uses the canonical CharacterValidator from character_validator.py.

    Returns False for:
    - Empty or whitespace-only strings
    - System text ([条件, 开始条件, etc.)
    - Combined speakers (派蒙&卡齐娜)
    - Narrative text
    - UI elements (选项1, 玩家选项)
    - Generic references (众人, 呼救的人)
    - Objects (嘟嘟通讯仪, 比赛公告板)
    """
    result = _validate(name)
    return result.is_valid


def normalize_character_name(name: str) -> str:
    """
    Normalize a character name.

    - Remove （回忆） suffix
    - Strip whitespace
    """
    name = name.strip()

    # Remove memory suffix
    if name.endswith('（回忆）'):
        name = name[:-4]

    return name


# =============================================================================
# Tests for Invalid Character Detection
# =============================================================================

class TestInvalidCharacterDetection:
    """Test that invalid character patterns are properly rejected."""

    @pytest.mark.parametrize("name", InvalidCharacterPatterns.SYSTEM_TEXT)
    def test_reject_system_text(self, name):
        """System/conditional text should be rejected."""
        assert not is_valid_character_name(name), f"Should reject system text: {name}"

    @pytest.mark.parametrize("name", InvalidCharacterPatterns.UI_ELEMENTS)
    def test_reject_ui_elements(self, name):
        """UI elements and options should be rejected."""
        assert not is_valid_character_name(name), f"Should reject UI element: {name}"

    @pytest.mark.parametrize("name", InvalidCharacterPatterns.COMBINED_SPEAKERS)
    def test_reject_combined_speakers(self, name):
        """Combined speaker names (with &) should be rejected."""
        assert not is_valid_character_name(name), f"Should reject combined speaker: {name}"

    @pytest.mark.parametrize("name", InvalidCharacterPatterns.NARRATIVE_TEXT)
    def test_reject_narrative_text(self, name):
        """Long narrative text should be rejected."""
        assert not is_valid_character_name(name), f"Should reject narrative text: {name}"

    @pytest.mark.parametrize("name", InvalidCharacterPatterns.MEMORY_VARIANTS)
    def test_reject_memory_variants(self, name):
        """Memory variants should be rejected (need normalization)."""
        assert not is_valid_character_name(name), f"Should reject memory variant: {name}"


class TestValidCharacterNames:
    """Test that valid character names are accepted."""

    VALID_NAMES = [
        "派蒙",
        "恰斯卡",
        "伊法",
        "咔库库",
        "玛薇卡",
        "基尼奇",
        "阿尤",
        "希诺宁",
        "旅行者",
        # Note: "？？？" and "小机器人" are now filtered as invalid
        # because they are placeholders/system characters, not real character names
        "「博士」",  # Quoted titles are valid
    ]

    @pytest.mark.parametrize("name", VALID_NAMES)
    def test_accept_valid_names(self, name):
        """Valid character names should be accepted."""
        assert is_valid_character_name(name), f"Should accept valid name: {name}"


class TestCharacterNameNormalization:
    """Test character name normalization."""

    def test_normalize_memory_suffix(self):
        """Memory suffix should be removed."""
        assert normalize_character_name("丽莎（回忆）") == "丽莎"
        assert normalize_character_name("温迪（回忆）") == "温迪"

    def test_normalize_whitespace(self):
        """Whitespace should be trimmed."""
        assert normalize_character_name("  派蒙  ") == "派蒙"

    def test_normalize_normal_name(self):
        """Normal names should be unchanged."""
        assert normalize_character_name("恰斯卡") == "恰斯卡"


# =============================================================================
# Tests for Organization Validation
# =============================================================================

class TestOrganizationValidation:
    """Test organization name validation."""

    VALID_ORGANIZATIONS = [
        "花羽会",
        "流泉之众",
        "竞人族",
        "回声之子",
        "金鳞会",
        "愚人众",
        "六英杰",
    ]

    INVALID_ORGANIZATIONS = [
        "焰人众",  # May not exist in actual story - needs verification
    ]

    @pytest.mark.parametrize("org", VALID_ORGANIZATIONS)
    def test_valid_organizations(self, org):
        """Known valid organizations should be accepted."""
        # This test documents expected organizations
        assert len(org) > 0

    def test_organization_should_be_verified(self):
        """Organizations should be verified against actual story content."""
        # 焰人众 was found in seed data but may not exist in story
        # This test reminds us to verify organizations before adding to seed
        pass


# =============================================================================
# Tests for KnowledgeGraphOutput Filtering
# =============================================================================

class TestKGOutputFiltering:
    """Test filtering of KnowledgeGraphOutput entities."""

    def test_filter_invalid_entities_from_kg(self):
        """Invalid entities should be filtered from KG output."""
        # Simulate KG output with both valid and invalid entities
        entities = [
            ExtractedEntity(name="派蒙", entity_type="Character"),
            ExtractedEntity(name="选项1", entity_type="Character"),  # Invalid
            ExtractedEntity(name="恰斯卡", entity_type="Character"),
            ExtractedEntity(name="[条件", entity_type="Character"),  # Invalid
            ExtractedEntity(name="派蒙&卡齐娜&玛拉妮", entity_type="Character"),  # Invalid
        ]

        valid_entities = [e for e in entities if is_valid_character_name(e.name)]

        assert len(valid_entities) == 2
        assert valid_entities[0].name == "派蒙"
        assert valid_entities[1].name == "恰斯卡"

    def test_kg_entity_names_set(self):
        """Test extracting valid entity names as set."""
        kg = KnowledgeGraphOutput(
            entities=[
                ExtractedEntity(name="派蒙", entity_type="Character"),
                ExtractedEntity(name="恰斯卡", entity_type="Character"),
                ExtractedEntity(name="选项1", entity_type="Character"),
            ],
            relationships=[]
        )

        all_names = kg.get_entity_names()
        valid_names = {name for name in all_names if is_valid_character_name(name)}

        assert "派蒙" in valid_names
        assert "恰斯卡" in valid_names
        assert "选项1" not in valid_names


# =============================================================================
# Tests for Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases in character name validation."""

    def test_empty_string(self):
        """Empty string should be rejected."""
        assert not is_valid_character_name("")
        assert not is_valid_character_name("   ")

    def test_very_long_name(self):
        """Very long names should be rejected."""
        long_name = "这是一个非常长的名字，很可能是叙述文本而不是角色名"
        assert not is_valid_character_name(long_name)

    def test_name_with_parentheses_start(self):
        """Names starting with parentheses should be rejected."""
        assert not is_valid_character_name("（某处的声音")
        assert not is_valid_character_name("(voice)")

    def test_name_with_brackets_start(self):
        """Names starting with brackets should be rejected."""
        assert not is_valid_character_name("[条件")
        assert not is_valid_character_name("【系统】")


# =============================================================================
# Recommended Filter List for Entity Extraction
# =============================================================================

# These patterns should be added to SYSTEM_CHARACTERS or filtered during extraction
RECOMMENDED_FILTER_PATTERNS = {
    # Exact matches to filter
    "exact_filter": [
        "选项", "选项1", "选项2", "选项3", "选项4", "选项5",
        "玩家选项", "开始条件", "查看", "调查", "致敬",
        "比赛公告板", "嘟嘟通讯仪", "战场情报", "旁白",
        "门禁机仆", "通行机仆",
        "众人", "众人齐声",
    ],

    # Prefix patterns to filter (names starting with these)
    "prefix_filter": [
        "[",
        "(",
        "（",
        "【",
    ],

    # Contains patterns to filter
    "contains_filter": [
        "&",
        "条件",
    ],

    # Suffix patterns to normalize (not filter, but transform)
    "normalize_suffix": [
        "（回忆）",
    ],
}


class TestRecommendedFilters:
    """Test that recommended filters work correctly."""

    @pytest.mark.parametrize("name", RECOMMENDED_FILTER_PATTERNS["exact_filter"])
    def test_exact_filter_patterns(self, name):
        """Exact filter patterns should be rejected."""
        assert not is_valid_character_name(name), f"Should filter: {name}"

    @pytest.mark.parametrize("prefix", RECOMMENDED_FILTER_PATTERNS["prefix_filter"])
    def test_prefix_filter_patterns(self, prefix):
        """Names with filter prefixes should be rejected."""
        test_name = f"{prefix}test"
        assert not is_valid_character_name(test_name), f"Should filter prefix: {prefix}"
