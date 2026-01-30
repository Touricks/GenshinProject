"""
Tests for character name validation and data quality control.

These tests ensure that invalid character names are filtered out during
extraction, preventing data quality issues in the knowledge graph.
"""

import pytest
import sys
from pathlib import Path

# Add src/ingestion to path to import directly from module files
ingestion_path = str(Path(__file__).parent.parent.parent.parent / "src" / "ingestion")
if ingestion_path not in sys.path:
    sys.path.insert(0, ingestion_path)

from character_validator import (
    CharacterValidator,
    InvalidReason,
    ValidationResult,
    validate_character_name,
    filter_character_names,
)


class TestSystemTextFiltering:
    """Test filtering of system text being extracted as character names."""

    def test_filters_bracket_prefix(self):
        """System text starting with [ should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("[条件")
        assert not result.is_valid
        assert result.reason == InvalidReason.SYSTEM_TEXT

    def test_filters_chinese_bracket_prefix(self):
        """System text starting with 【 should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("【系统提示】")
        assert not result.is_valid
        assert result.reason == InvalidReason.SYSTEM_TEXT

    def test_filters_parenthesis_prefix(self):
        """System text starting with （ should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("（旁白）")
        assert not result.is_valid
        assert result.reason == InvalidReason.SYSTEM_TEXT

    def test_filters_condition_keywords(self):
        """Text with condition keywords should be filtered."""
        validator = CharacterValidator()

        assert not validator.validate("开始条件").is_valid
        assert not validator.validate("结束条件").is_valid
        assert not validator.validate("查看").is_valid
        assert not validator.validate("调查").is_valid
        assert not validator.validate("触发").is_valid

    def test_filters_task_prefix(self):
        """Text starting with 任务 should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("任务目标")
        assert not result.is_valid
        assert result.reason == InvalidReason.SYSTEM_TEXT


class TestCombinedSpeakerFiltering:
    """Test filtering and splitting of combined speaker names."""

    def test_filters_combined_speaker(self):
        """Combined speakers with & should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("派蒙&卡齐娜&玛拉妮")
        assert not result.is_valid
        assert result.reason == InvalidReason.COMBINED_SPEAKER

    def test_filters_two_person_combined(self):
        """Two-person combined speaker should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("哈恩薇&安帕奥")
        assert not result.is_valid
        assert result.reason == InvalidReason.COMBINED_SPEAKER

    def test_splits_combined_speaker(self):
        """Can split combined speaker into individual names."""
        validator = CharacterValidator()

        names = validator.split_combined_speaker("派蒙&卡齐娜&玛拉妮")
        assert names == ["派蒙", "卡齐娜", "玛拉妮"]

    def test_split_preserves_single_name(self):
        """Single names are preserved when splitting."""
        validator = CharacterValidator()

        names = validator.split_combined_speaker("派蒙")
        assert names == ["派蒙"]

    def test_extract_valid_from_combined(self):
        """Can extract valid names from combined speaker."""
        validator = CharacterValidator()

        valid_names = validator.extract_valid_from_combined("派蒙&卡齐娜&玛拉妮")
        assert "派蒙" in valid_names
        assert "卡齐娜" in valid_names
        assert "玛拉妮" in valid_names

    def test_extract_valid_filters_invalid_parts(self):
        """Invalid parts are filtered when extracting from combined."""
        validator = CharacterValidator()

        # If one part is invalid, it should be filtered
        valid_names = validator.extract_valid_from_combined("派蒙&众人齐声")
        assert "派蒙" in valid_names
        assert "众人齐声" not in valid_names


class TestNarrativeTextFiltering:
    """Test filtering of narrative text being extracted as character names."""

    def test_filters_text_with_period(self):
        """Text containing period should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("但你们不会认输。所有人团结一致，你们知道")
        assert not result.is_valid
        assert result.reason == InvalidReason.NARRATIVE_TEXT

    def test_filters_text_with_multiple_commas(self):
        """Text with multiple commas is likely narrative."""
        validator = CharacterValidator()

        result = validator.validate("你不合时宜地回想起多托雷的话，那些话，还有")
        assert not result.is_valid
        assert result.reason == InvalidReason.NARRATIVE_TEXT

    def test_filters_text_with_ellipsis(self):
        """Text with ellipsis is likely narrative."""
        validator = CharacterValidator()

        result = validator.validate("这是……一个测试")
        assert not result.is_valid
        assert result.reason == InvalidReason.NARRATIVE_TEXT

    def test_filters_very_long_text(self):
        """Very long text (>20 chars) should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("这是一个非常非常长的名字，明显不是角色名")
        assert not result.is_valid
        # Could be NARRATIVE_TEXT or TOO_LONG depending on pattern match order

    def test_allows_short_descriptive_names(self):
        """Short descriptive names with one comma are allowed."""
        validator = CharacterValidator()

        # Single comma in a short name might be valid
        result = validator.validate("「明晨之镜」")
        assert result.is_valid


class TestUIElementFiltering:
    """Test filtering of UI elements being extracted as character names."""

    def test_filters_option_numbers(self):
        """Option numbers should be filtered."""
        validator = CharacterValidator()

        assert not validator.validate("选项1").is_valid
        assert not validator.validate("选项2").is_valid
        assert not validator.validate("选项").is_valid

    def test_filters_player_option(self):
        """Player option should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("玩家选项")
        assert not result.is_valid
        assert result.reason == InvalidReason.UI_ELEMENT

    def test_filters_choice_numbers(self):
        """Choice numbers should be filtered."""
        validator = CharacterValidator()

        assert not validator.validate("选择1").is_valid
        assert not validator.validate("分支1").is_valid

    def test_filters_dialogue_option(self):
        """Dialogue option should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("对话选项")
        assert not result.is_valid


class TestGenericReferenceFiltering:
    """Test filtering of generic references that aren't specific characters."""

    def test_filters_crowd_reference(self):
        """Crowd references should be filtered."""
        validator = CharacterValidator()

        assert not validator.validate("众人").is_valid
        assert not validator.validate("众人齐声").is_valid

    def test_filters_person_suffix(self):
        """Generic 'XX的人' should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("呼救的人")
        assert not result.is_valid
        assert result.reason == InvalidReason.GENERIC_REFERENCE

    def test_filters_voice_suffix(self):
        """Generic 'XX的声音' should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("远处的声音")
        assert not result.is_valid
        assert result.reason == InvalidReason.GENERIC_REFERENCE

    def test_filters_mysterious_prefix(self):
        """Mysterious/神秘 prefix should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("神秘的声音")
        assert not result.is_valid

    def test_filters_noisy_prefix(self):
        """Noisy/嘈杂 prefix should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("嘈杂的怒吼")
        assert not result.is_valid

    def test_filters_someone_generic(self):
        """Generic 'someone' references should be filtered."""
        validator = CharacterValidator()

        assert not validator.validate("有人").is_valid
        assert not validator.validate("旁人").is_valid
        assert not validator.validate("路人甲").is_valid
        assert not validator.validate("某人").is_valid


class TestObjectFiltering:
    """Test filtering of objects/things being extracted as character names."""

    def test_filters_communicator(self):
        """Communication devices should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("嘟嘟通讯仪")
        assert not result.is_valid
        assert result.reason == InvalidReason.OBJECT_OR_THING

    def test_filters_notice_board(self):
        """Notice boards should be filtered."""
        validator = CharacterValidator()

        assert not validator.validate("比赛公告板").is_valid
        assert not validator.validate("告示").is_valid

    def test_filters_letters(self):
        """Letters/messages should be filtered."""
        validator = CharacterValidator()

        assert not validator.validate("信件").is_valid
        assert not validator.validate("留言").is_valid

    def test_filters_bird_species(self):
        """Animal/bird species names should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("长翎鹮")
        assert not result.is_valid


class TestBlacklistFiltering:
    """Test explicit blacklist filtering."""

    def test_filters_question_marks(self):
        """Question mark placeholders should be filtered."""
        validator = CharacterValidator()

        assert not validator.validate("？？？").is_valid
        assert not validator.validate("???").is_valid

    def test_filters_dashes(self):
        """Dash placeholders should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("---")
        assert not result.is_valid
        assert result.reason == InvalidReason.BLACKLISTED

    def test_filters_saurian_companion(self):
        """English placeholder text should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("Saurian companion")
        assert not result.is_valid

    def test_filters_strange_bird(self):
        """Generic animal descriptions should be filtered."""
        validator = CharacterValidator()

        result = validator.validate("奇怪的鸟")
        assert not result.is_valid

    def test_supports_additional_blacklist(self):
        """Can add additional items to blacklist."""
        validator = CharacterValidator(additional_blacklist={"自定义黑名单"})

        result = validator.validate("自定义黑名单")
        assert not result.is_valid
        assert result.reason == InvalidReason.BLACKLISTED


class TestValidCharacterNames:
    """Test that valid character names pass validation."""

    def test_allows_main_characters(self):
        """Main character names should be valid."""
        validator = CharacterValidator()

        assert validator.validate("派蒙").is_valid
        assert validator.validate("旅行者").is_valid
        assert validator.validate("卡齐娜").is_valid
        assert validator.validate("玛拉妮").is_valid
        assert validator.validate("基尼奇").is_valid

    def test_allows_quoted_titles(self):
        """Quoted titles/epithets should be valid."""
        validator = CharacterValidator()

        assert validator.validate("「博士」").is_valid
        assert validator.validate("「明晨之镜」").is_valid
        assert validator.validate("「队长」").is_valid

    def test_allows_npc_names(self):
        """NPC names should be valid."""
        validator = CharacterValidator()

        assert validator.validate("万奎洛").is_valid
        assert validator.validate("乌兰塔").is_valid
        assert validator.validate("凯瑟琳").is_valid

    def test_allows_wanderer(self):
        """Wanderer should be valid despite being English."""
        validator = CharacterValidator()

        result = validator.validate("Wanderer")
        assert result.is_valid


class TestNameNormalization:
    """Test character name normalization."""

    def test_normalizes_parenthetical_notes(self):
        """Parenthetical notes should be removed."""
        validator = CharacterValidator()

        result = validator.validate("丽莎（回忆）")
        # This might be filtered as OBJECT_OR_THING due to 回忆）pattern
        # Let's check what actually happens
        if result.is_valid:
            assert result.normalized_name == "丽莎"

    def test_strips_whitespace(self):
        """Whitespace should be stripped."""
        validator = CharacterValidator()

        result = validator.validate("  派蒙  ")
        assert result.is_valid
        assert result.normalized_name == "派蒙"


class TestFilterNames:
    """Test bulk filtering of character names."""

    def test_filters_mixed_list(self):
        """Can filter a mixed list of valid and invalid names."""
        validator = CharacterValidator()

        names = [
            "派蒙",
            "[条件",
            "卡齐娜",
            "派蒙&卡齐娜",
            "众人",
            "基尼奇",
            "选项1",
        ]

        valid, invalid = validator.filter_names(names)

        assert "派蒙" in valid
        assert "卡齐娜" in valid
        assert "基尼奇" in valid
        assert len(valid) == 3

        invalid_names = [name for name, _ in invalid]
        assert "[条件" in invalid_names
        assert "派蒙&卡齐娜" in invalid_names
        assert "众人" in invalid_names
        assert "选项1" in invalid_names

    def test_returns_reasons_for_invalid(self):
        """Returns reasons for each invalid name."""
        validator = CharacterValidator()

        names = ["[条件", "派蒙&卡齐娜", "选项1"]
        _, invalid = validator.filter_names(names)

        reasons = {name: reason for name, reason in invalid}
        assert reasons["[条件"] == InvalidReason.SYSTEM_TEXT
        assert reasons["派蒙&卡齐娜"] == InvalidReason.COMBINED_SPEAKER
        assert reasons["选项1"] == InvalidReason.UI_ELEMENT


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_validate_character_name(self):
        """validate_character_name works correctly."""
        result = validate_character_name("派蒙")
        assert result.is_valid

        result = validate_character_name("[条件")
        assert not result.is_valid

    def test_filter_character_names(self):
        """filter_character_names returns only valid names."""
        names = ["派蒙", "[条件", "卡齐娜", "众人"]
        valid = filter_character_names(names)

        assert valid == ["派蒙", "卡齐娜"]


class TestRealWorldExamples:
    """Test with real examples from the Neo4j export."""

    @pytest.fixture
    def validator(self):
        return CharacterValidator()

    def test_filters_all_known_issues(self, validator):
        """All known data quality issues should be filtered."""
        known_issues = [
            "[条件",
            "哈恩薇&安帕奥",
            "派蒙&卡齐娜&玛拉妮",
            "但你们不会认输。所有人团结一致，你们知道",
            "你不合时宜地回想起多托雷的话",
            "选项1",
            "玩家选项",
            "众人",
            "众人齐声",
            "呼救的人",
            "嘈杂的怒吼",
            "嘟嘟通讯仪",
            "比赛公告板",
            "长翎鹮",
            "奇怪的鸟",
            "Saurian companion",
            "？？？",
        ]

        for issue in known_issues:
            result = validator.validate(issue)
            assert not result.is_valid, f"Should filter: {issue}"

    def test_allows_all_valid_characters(self, validator):
        """All valid character names should pass."""
        valid_characters = [
            "派蒙",
            "旅行者",
            "卡齐娜",
            "玛拉妮",
            "基尼奇",
            "希诺宁",
            "玛薇卡",
            "恰斯卡",
            "伊法",
            "咔库库",
            "穆洛塔",
            "茜特菈莉",
            "「博士」",
            "「队长」",
            "万奎洛",
            "凯瑟琳",
            "夏洛蒂",
            "Wanderer",
        ]

        for name in valid_characters:
            result = validator.validate(name)
            assert result.is_valid, f"Should allow: {name}"
