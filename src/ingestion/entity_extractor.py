"""
Entity extraction from dialogue files.

Extracts characters, organizations, locations, and events from game dialogue text.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass

from ..models.entities import (
    Character,
    Organization,
    Location,
    KNOWN_ORGANIZATIONS,
    MAIN_CHARACTERS,
    SYSTEM_CHARACTERS,
)
from .character_validator import CharacterValidator


@dataclass
class DocumentMetadata:
    """Metadata extracted from dialogue file headers."""

    task_id: str
    task_name: str
    chapter_number: int
    chapter_name: str
    series_name: Optional[str] = None
    source_url: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class ExtractionResult:
    """Result of entity extraction from a dialogue file."""

    metadata: DocumentMetadata
    characters: Set[str]
    locations: Set[str]
    scenes: List[str]
    raw_text: str


class EntityExtractor:
    """Extract entities from dialogue text files."""

    # Regex patterns for header parsing
    HEADER_PATTERNS = {
        "task_chapter": r"^# (.+) - 第(\d+)章[：:](.+)$",
        "series": r"^# (.+第.+幕.*)$",
        "source": r"^# 来源[：:](.+)$",
        "summary_start": r"^## 剧情简介$",
    }

    # Regex for character extraction (excludes lines starting with #)
    CHARACTER_PATTERN = re.compile(r"^(?!#)([^：\n]+)：", re.MULTILINE)

    # Regex for location extraction from scene headers
    LOCATION_PATTERNS = [
        re.compile(r"^## 前往(.+)$", re.MULTILINE),
        re.compile(r"^## 到达(.+)$", re.MULTILINE),
        re.compile(r"^## 进入(.+)$", re.MULTILINE),
    ]

    # Regex for scene headers
    SCENE_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)

    def __init__(self):
        """Initialize the entity extractor."""
        self.known_orgs = set(KNOWN_ORGANIZATIONS.keys())
        self.known_characters = set(MAIN_CHARACTERS.keys())
        self.validator = CharacterValidator()

    def extract_from_file(self, file_path: Path) -> ExtractionResult:
        """
        Extract all entities from a dialogue file.

        Args:
            file_path: Path to the dialogue file

        Returns:
            ExtractionResult containing extracted entities and metadata
        """
        content = file_path.read_text(encoding="utf-8")

        # Extract task_id from directory name
        task_id = file_path.parent.name

        # Extract chapter number from filename
        chapter_match = re.search(r"chapter(\d+)", file_path.name)
        chapter_number = int(chapter_match.group(1)) if chapter_match else 0

        # Parse document metadata
        metadata = self._parse_header(content, task_id, chapter_number)

        # Extract entities
        characters = self.extract_characters(content)
        locations = self.extract_locations(content)
        scenes = self.extract_scenes(content)

        return ExtractionResult(
            metadata=metadata,
            characters=characters,
            locations=locations,
            scenes=scenes,
            raw_text=content,
        )

    def _parse_header(
        self, content: str, task_id: str, chapter_number: int
    ) -> DocumentMetadata:
        """Parse the file header to extract document metadata."""
        lines = content.split("\n")

        task_name = ""
        chapter_name = ""
        series_name = None
        source_url = None
        summary = None

        in_summary = False
        summary_lines = []

        for line in lines[:30]:  # Only check first 30 lines for header
            # Task and chapter info
            task_match = re.match(self.HEADER_PATTERNS["task_chapter"], line)
            if task_match:
                task_name = task_match.group(1)
                chapter_name = task_match.group(3)
                continue

            # Series name
            series_match = re.match(self.HEADER_PATTERNS["series"], line)
            if series_match and not task_name:
                series_name = series_match.group(1)
                continue

            # Source URL
            source_match = re.match(self.HEADER_PATTERNS["source"], line)
            if source_match:
                source_url = source_match.group(1)
                continue

            # Summary section
            if re.match(self.HEADER_PATTERNS["summary_start"], line):
                in_summary = True
                continue

            if in_summary:
                if line.startswith("---") or line.startswith("## "):
                    in_summary = False
                    summary = "\n".join(summary_lines).strip()
                elif line.strip():
                    summary_lines.append(line)

        return DocumentMetadata(
            task_id=task_id,
            task_name=task_name,
            chapter_number=chapter_number,
            chapter_name=chapter_name,
            series_name=series_name,
            source_url=source_url,
            summary=summary,
        )

    def extract_characters(self, text: str) -> Set[str]:
        """
        Extract character names from dialogue text.

        Uses CharacterValidator to filter out:
        - System text ([条件, 开始条件, etc.)
        - Combined speakers (派蒙&卡齐娜)
        - Narrative text
        - UI elements (选项1, 玩家选项)
        - Generic references (众人, 呼救的人)
        - Objects (嘟嘟通讯仪)

        Args:
            text: Dialogue text content

        Returns:
            Set of valid character names found in the text
        """
        raw_matches = self.CHARACTER_PATTERN.findall(text)

        # Clean and filter using validator
        characters = set()
        for name in raw_matches:
            name = name.strip()

            # Skip legacy system characters (kept for backwards compatibility)
            if name in SYSTEM_CHARACTERS:
                continue

            # Use validator for comprehensive filtering
            result = self.validator.validate(name)
            if result.is_valid:
                # Use normalized name if available
                characters.add(result.normalized_name or result.name)
            elif result.reason and result.reason.value == "combined_speaker":
                # For combined speakers, extract individual valid names
                valid_parts = self.validator.extract_valid_from_combined(name)
                characters.update(valid_parts)

        return characters

    def extract_locations(self, text: str) -> Set[str]:
        """
        Extract location names from scene headers.

        Args:
            text: Dialogue text content

        Returns:
            Set of location names found in the text
        """
        locations = set()

        for pattern in self.LOCATION_PATTERNS:
            matches = pattern.findall(text)
            for loc in matches:
                loc = loc.strip()
                if loc and len(loc) <= 30:
                    locations.add(loc)

        return locations

    def extract_scenes(self, text: str) -> List[str]:
        """
        Extract scene titles from the dialogue.

        Args:
            text: Dialogue text content

        Returns:
            List of scene titles in order
        """
        scenes = []
        matches = self.SCENE_PATTERN.findall(text)

        for scene in matches:
            scene = scene.strip()
            # Skip special headers
            if scene in ["剧情简介", "选项"]:
                continue
            scenes.append(scene)

        return scenes

    def extract_organizations_mentioned(self, text: str) -> Set[str]:
        """
        Find known organizations mentioned in the text.

        Args:
            text: Dialogue text content

        Returns:
            Set of organization names mentioned
        """
        mentioned = set()
        for org_name in self.known_orgs:
            if org_name in text:
                mentioned.add(org_name)
        return mentioned

    def get_character_info(self, name: str) -> Optional[Character]:
        """
        Get character info from known characters database.

        Args:
            name: Character name

        Returns:
            Character object if known, None otherwise
        """
        # Check direct match
        if name in MAIN_CHARACTERS:
            return MAIN_CHARACTERS[name]

        # Check aliases
        for char in MAIN_CHARACTERS.values():
            if name in char.aliases:
                return char

        return None

    def normalize_character_name(self, name: str) -> str:
        """
        Normalize character name to canonical form.

        Args:
            name: Raw character name

        Returns:
            Canonical character name
        """
        # Map common aliases
        alias_map = {
            "玩家": "旅行者",
            "杜麦尼": "旅行者",
            "Traveler": "旅行者",
            "阿乔": "阿尤",
        }

        return alias_map.get(name, name)


def extract_all_entities(data_dir: str = "Data/") -> Dict[str, ExtractionResult]:
    """
    Extract entities from all dialogue files in the data directory.

    Args:
        data_dir: Path to the data directory

    Returns:
        Dictionary mapping file paths to extraction results
    """
    extractor = EntityExtractor()
    data_path = Path(data_dir)
    results = {}

    for task_dir in sorted(data_path.iterdir()):
        if not task_dir.is_dir():
            continue

        for chapter_file in sorted(task_dir.glob("chapter*_dialogue.txt")):
            file_key = f"{task_dir.name}/{chapter_file.name}"
            try:
                result = extractor.extract_from_file(chapter_file)
                results[file_key] = result
            except Exception as e:
                print(f"Error processing {file_key}: {e}")

    return results


if __name__ == "__main__":
    # Test extraction
    import sys

    data_dir = sys.argv[1] if len(sys.argv) > 1 else "Data/"
    results = extract_all_entities(data_dir)

    print(f"\nExtracted from {len(results)} files:")
    print("-" * 50)

    all_characters = set()
    all_locations = set()

    for file_key, result in results.items():
        all_characters.update(result.characters)
        all_locations.update(result.locations)
        print(f"\n{file_key}:")
        print(f"  Task: {result.metadata.task_name}")
        print(f"  Chapter: {result.metadata.chapter_number} - {result.metadata.chapter_name}")
        print(f"  Characters: {len(result.characters)}")
        print(f"  Locations: {len(result.locations)}")
        print(f"  Scenes: {len(result.scenes)}")

    print("\n" + "=" * 50)
    print(f"Total unique characters: {len(all_characters)}")
    print(f"Characters: {sorted(all_characters)}")
    print(f"\nTotal unique locations: {len(all_locations)}")
    print(f"Locations: {sorted(all_locations)}")
