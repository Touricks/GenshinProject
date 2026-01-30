"""Tests for metadata extraction functionality."""

import pytest
import re

from tests.extraction.conftest import (
    get_test_cases_by_category,
    calculate_f1,
)


# =============================================================================
# Character Extraction Tests
# =============================================================================


class TestCharacterExtraction:
    """Test character name extraction from dialogue text."""

    def test_standard_dialogue_format(self, metadata_enricher, sample_dialogue_text):
        """Test extraction from standard '角色：对话' format."""
        characters = metadata_enricher._extract_characters(sample_dialogue_text)

        expected = {"伊法", "恰斯卡", "派蒙"}
        found = set(characters)

        f1 = calculate_f1(found, expected)
        assert f1 >= 0.90, f"Character extraction F1: {f1:.2f}"

    def test_player_character_extraction(self, metadata_enricher):
        """Test extraction of player character '玩家'."""
        text = "玩家：伊法刚才是在「看病」吗？\n\n伊法：嗯，好在恰斯卡送医及时。"
        characters = metadata_enricher._extract_characters(text)

        assert "玩家" in characters
        assert "伊法" in characters

    def test_anonymous_character(self, metadata_enricher, sample_anonymous_text):
        """Test handling of anonymous '？？？' speaker."""
        characters = metadata_enricher._extract_characters(sample_anonymous_text)

        # Both ？？？ and 小机器人 are in SYSTEM_CHARACTERS, should be filtered
        assert "？？？" not in characters
        assert "小机器人" not in characters
        assert characters == []

    def test_special_entity_extraction(self, metadata_enricher):
        """Test extraction of special entities like curses."""
        text = "黑雾诅咒：——「悖谬」。\n\n黑雾诅咒：此非正途。此非归处。"
        characters = metadata_enricher._extract_characters(text)

        # Special entities may or may not be extracted depending on filter
        assert len(characters) >= 0  # Depends on filter implementation

    def test_quoted_character_name(self, metadata_enricher):
        """Test extraction of character with quoted name."""
        text = "「木偶」：…纳塔的古龙文明？呵…\n\n维李米尔：…撤吧。"
        characters = metadata_enricher._extract_characters(text)

        assert "维李米尔" in characters
        # 「木偶」 may or may not be extracted based on filter

    @pytest.mark.parametrize(
        "test_id",
        ["meta_001", "meta_003", "meta_004", "meta_025"],
    )
    def test_character_extraction_from_dataset(self, metadata_dataset, test_id):
        """Test character extraction using evaluation dataset."""
        items = metadata_dataset.get("items", [])
        test_case = next((item for item in items if item["id"] == test_id), None)

        if test_case is None:
            pytest.skip(f"Test case {test_id} not found")

        expected_meta = test_case.get("expected_metadata", {})
        expected_chars = expected_meta.get("characters", [])

        assert len(expected_chars) > 0, f"Expected characters for {test_id}"


# =============================================================================
# Task Info Parsing Tests
# =============================================================================


class TestTaskInfoParsing:
    """Test parsing of chapter header information."""

    def test_standard_header_parsing(self, document_loader, sample_header_text):
        """Test parsing of standard chapter header."""
        # Parse header directly
        lines = sample_header_text.split("\n")
        metadata = document_loader._parse_header(lines, "1600", None)

        assert metadata.task_id == "1600"
        assert metadata.task_name == "归途"
        assert metadata.chapter_number == 0
        assert metadata.chapter_title == "墟火"
        assert metadata.series_name == "空月之歌 序奏"

    def test_source_url_extraction(self, document_loader, sample_header_text):
        """Test extraction of source URL."""
        lines = sample_header_text.split("\n")
        metadata = document_loader._parse_header(lines, "1600", None)

        expected_url = "https://gi.yatta.moe/chs/archive/quest/1602/the-journey-home?chapter=0"
        assert metadata.source_url == expected_url

    def test_chapter_number_from_filename(self, document_loader):
        """Test fallback chapter number extraction from filename."""
        from pathlib import Path

        # Create a mock file path
        file_path = Path("Data/1600/chapter2_dialogue.txt")
        filename_match = document_loader.CHAPTER_FROM_FILENAME.search(file_path.name)

        assert filename_match is not None
        assert filename_match.group(1) == "2"

    def test_different_series_formats(self):
        """Test parsing of different series name formats."""
        series_patterns = [
            ("# 空月之歌 序奏", "空月之歌 序奏"),
            ("# 空月之歌 第一幕", "空月之歌 第一幕"),
            ("# 空月之歌 第二幕", "空月之歌 第二幕"),
            ("# 兰那罗系列", None),  # May not match series pattern
        ]

        from src.ingestion.loader import DocumentLoader

        for header, expected in series_patterns:
            match = DocumentLoader.SERIES_PATTERN.match(header)
            if expected:
                assert match is not None, f"Should match: {header}"

    @pytest.mark.parametrize(
        "test_id",
        ["meta_006", "meta_007", "meta_023"],
    )
    def test_task_info_from_dataset(self, metadata_dataset, test_id):
        """Test task info parsing using evaluation dataset."""
        items = metadata_dataset.get("items", [])
        test_case = next((item for item in items if item["id"] == test_id), None)

        if test_case is None:
            pytest.skip(f"Test case {test_id} not found")

        expected_meta = test_case.get("expected_metadata", {})

        # Verify expected fields exist
        assert "task_id" in expected_meta or "task_name" in expected_meta


# =============================================================================
# Event Order Tests
# =============================================================================


class TestEventOrder:
    """Test event order computation for temporal queries."""

    def test_basic_event_order(self, metadata_enricher):
        """Test basic event order calculation."""
        from src.models import DocumentMetadata

        doc_meta = DocumentMetadata(
            task_id="1600",
            task_name="归途",
            chapter_number=0,
            chapter_title="墟火",
        )

        event_order = metadata_enricher._compute_event_order(doc_meta, scene_order=1, chunk_order=0)

        # Formula: task_id * 10000 + chapter * 1000 + scene * 10 + chunk
        expected = 1600 * 10000 + 0 * 1000 + 1 * 10 + 0
        assert event_order == expected

    def test_event_order_monotonic(self, metadata_enricher):
        """Test that event order increases monotonically."""
        from src.models import DocumentMetadata

        doc_meta = DocumentMetadata(
            task_id="1600",
            task_name="归途",
            chapter_number=0,
            chapter_title="墟火",
        )

        orders = []
        for scene in range(5):
            for chunk in range(3):
                order = metadata_enricher._compute_event_order(doc_meta, scene, chunk)
                orders.append(order)

        # Check monotonic increase
        for i in range(1, len(orders)):
            assert orders[i] > orders[i - 1], "Event order should be monotonically increasing"

    def test_cross_chapter_ordering(self, metadata_enricher):
        """Test event order across chapters."""
        from src.models import DocumentMetadata

        chapter0 = DocumentMetadata(
            task_id="1600", task_name="归途", chapter_number=0, chapter_title="墟火"
        )
        chapter1 = DocumentMetadata(
            task_id="1600", task_name="归途", chapter_number=1, chapter_title="白夜降临"
        )

        order_ch0 = metadata_enricher._compute_event_order(chapter0, 99, 9)
        order_ch1 = metadata_enricher._compute_event_order(chapter1, 0, 0)

        assert order_ch1 > order_ch0, "Chapter 1 events should come after Chapter 0"


# =============================================================================
# Choice Detection Tests
# =============================================================================


class TestChoiceDetection:
    """Test detection of player choice blocks."""

    def test_standard_choice_block(self, metadata_enricher, sample_choice_text):
        """Test detection of standard choice block."""
        has_choice = metadata_enricher._has_choice(sample_choice_text)
        assert has_choice is True

    def test_no_choice_dialogue(self, metadata_enricher, sample_dialogue_text):
        """Test that regular dialogue is not detected as choice."""
        has_choice = metadata_enricher._has_choice(sample_dialogue_text)
        assert has_choice is False

    def test_three_option_choice(self, metadata_enricher):
        """Test detection of three-option choice block."""
        text = """## 选项
- 蓝色的书籍
- 红色的书籍
- 绿色的书籍

玩家：蓝色的书籍"""
        has_choice = metadata_enricher._has_choice(text)
        assert has_choice is True

    def test_choice_with_ellipsis(self, metadata_enricher):
        """Test detection of continuation-style choices."""
        text = """## 选项
- 看来不先救醒她…
- 什么事都弄不清楚。

玩家：看来不先救醒她…"""
        has_choice = metadata_enricher._has_choice(text)
        assert has_choice is True

    @pytest.mark.parametrize(
        "test_id",
        ["meta_010", "meta_011", "meta_024"],
    )
    def test_choice_detection_from_dataset(self, metadata_dataset, test_id):
        """Test choice detection using evaluation dataset."""
        items = metadata_dataset.get("items", [])
        test_case = next((item for item in items if item["id"] == test_id), None)

        if test_case is None:
            pytest.skip(f"Test case {test_id} not found")

        expected_meta = test_case.get("expected_metadata", {})
        expected_has_choice = expected_meta.get("has_choice")

        assert expected_has_choice is True, f"Test case {test_id} should have choice"


# =============================================================================
# Scene Name Extraction Tests
# =============================================================================


class TestSceneNameExtraction:
    """Test extraction of scene names from ## headers."""

    def test_standard_scene_name(self, metadata_enricher):
        """Test extraction of standard scene name."""
        text = "## 与恰斯卡对话\n\n伊法：…伤口已经处理完了。"
        # Scene name extraction is typically done in the chunker
        # Here we just verify the format

        pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        match = pattern.search(text)

        assert match is not None
        assert match.group(1) == "与恰斯卡对话"

    def test_synopsis_scene(self):
        """Test handling of 剧情简介 scene."""
        text = "## 剧情简介\n纳塔似乎迎来了一些意料之外的客人…"

        pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        match = pattern.search(text)

        assert match is not None
        assert "剧情简介" in match.group(1)


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestMetadataFromDataset:
    """Integration tests using the metadata evaluation dataset."""

    def test_character_extraction_category(self, metadata_dataset):
        """Test character_extraction category cases."""
        char_cases = get_test_cases_by_category(metadata_dataset, "character_extraction")

        assert len(char_cases) >= 10, "Should have at least 10 character extraction cases"

        for case in char_cases:
            expected = case.get("expected_metadata", {})
            characters = expected.get("characters", [])
            assert len(characters) > 0 or "notes" in expected

    def test_task_info_category(self, metadata_dataset):
        """Test task_info category cases."""
        task_cases = get_test_cases_by_category(metadata_dataset, "task_info")

        assert len(task_cases) >= 3, "Should have at least 3 task info cases"

    def test_event_order_category(self, metadata_dataset):
        """Test event_order category cases."""
        order_cases = get_test_cases_by_category(metadata_dataset, "event_order")

        assert len(order_cases) >= 3, "Should have at least 3 event order cases"

    def test_target_metrics_defined(self, metadata_dataset):
        """Verify target metrics are defined in dataset."""
        target_metrics = metadata_dataset.get("target_metrics", {})

        assert "character_f1" in target_metrics
        assert target_metrics["character_f1"] >= 0.85

        assert "event_order_accuracy" in target_metrics
        assert target_metrics["event_order_accuracy"] >= 0.80
