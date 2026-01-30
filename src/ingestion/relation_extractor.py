"""
Relationship extraction from dialogue files.

Extracts relationships between entities using:
1. Co-occurrence analysis (characters in same scene)
2. Seed relationships (predefined from story analysis)
3. Keyword-based detection
"""

import re
from typing import List, Set, Tuple, Dict
from collections import defaultdict

from ..models.relationships import (
    Relationship,
    RelationType,
    SEED_RELATIONSHIPS,
    RELATIONSHIP_KEYWORDS,
)
from ..models.entities import MAIN_CHARACTERS
from .entity_extractor import EntityExtractor, ExtractionResult


class RelationExtractor:
    """Extract relationships between entities from dialogue text."""

    def __init__(self):
        """Initialize the relation extractor."""
        self.entity_extractor = EntityExtractor()
        self.seed_relationships = SEED_RELATIONSHIPS

    def extract_cooccurrence_relations(
        self,
        text: str,
        scene_delimiter: str = r"^---$|^## ",
    ) -> List[Relationship]:
        """
        Extract INTERACTS_WITH relationships from character co-occurrence.

        Characters appearing in the same scene are considered to interact.

        Args:
            text: Dialogue text content
            scene_delimiter: Regex pattern to split scenes

        Returns:
            List of INTERACTS_WITH relationships
        """
        relationships = []

        # Split text into scenes
        scenes = re.split(scene_delimiter, text, flags=re.MULTILINE)

        for scene in scenes:
            if not scene.strip():
                continue

            # Extract characters in this scene
            characters = self.entity_extractor.extract_characters(scene)
            char_list = list(characters)

            # Create pairwise interactions
            for i, char1 in enumerate(char_list):
                for char2 in char_list[i + 1 :]:
                    # Normalize character names
                    char1_norm = self.entity_extractor.normalize_character_name(char1)
                    char2_norm = self.entity_extractor.normalize_character_name(char2)

                    # Skip self-interactions
                    if char1_norm == char2_norm:
                        continue

                    # Create bidirectional relationship (sorted to avoid duplicates)
                    source, target = sorted([char1_norm, char2_norm])
                    relationships.append(
                        Relationship(source, target, RelationType.INTERACTS_WITH)
                    )

        # Remove duplicates
        seen = set()
        unique_relationships = []
        for rel in relationships:
            key = (rel.source, rel.target, rel.rel_type)
            if key not in seen:
                seen.add(key)
                unique_relationships.append(rel)

        return unique_relationships

    def extract_dialogue_relations(self, text: str) -> List[Relationship]:
        """
        Extract relationships from dialogue patterns.

        Looks for patterns like:
        - "A和B是朋友"
        - "A是B的伙伴"
        - Direct address patterns

        Args:
            text: Dialogue text content

        Returns:
            List of extracted relationships
        """
        relationships = []

        # Pattern: "A和B是{keyword}" or "A、B是{keyword}"
        for keyword, rel_type in RELATIONSHIP_KEYWORDS.items():
            pattern = rf"([^\s，。？！]+)[和、]([^\s，。？！]+)是{keyword}"
            matches = re.findall(pattern, text)
            for char1, char2 in matches:
                char1 = self.entity_extractor.normalize_character_name(char1)
                char2 = self.entity_extractor.normalize_character_name(char2)
                relationships.append(Relationship(char1, char2, rel_type))

        # Pattern: "A是B的{keyword}"
        for keyword, rel_type in RELATIONSHIP_KEYWORDS.items():
            pattern = rf"([^\s，。？！：]+)是([^\s，。？！：]+)的{keyword}"
            matches = re.findall(pattern, text)
            for char1, char2 in matches:
                char1 = self.entity_extractor.normalize_character_name(char1)
                char2 = self.entity_extractor.normalize_character_name(char2)
                relationships.append(Relationship(char1, char2, rel_type))

        return relationships

    def extract_organization_relations(
        self, characters: Set[str], text: str
    ) -> List[Relationship]:
        """
        Extract organization membership relationships.

        Uses known character-organization mappings and text mentions.

        Args:
            characters: Set of character names in the text
            text: Dialogue text content

        Returns:
            List of MEMBER_OF relationships
        """
        relationships = []

        for char_name in characters:
            # Normalize name
            char_norm = self.entity_extractor.normalize_character_name(char_name)

            # Check if character has known organization
            char_info = self.entity_extractor.get_character_info(char_norm)
            if char_info and char_info.tribe:
                relationships.append(
                    Relationship(
                        char_norm,
                        char_info.tribe,
                        RelationType.MEMBER_OF,
                        {"role": "member"},
                    )
                )

        return relationships

    def calculate_interaction_strength(
        self, relationships: List[Relationship]
    ) -> Dict[Tuple[str, str], int]:
        """
        Calculate interaction strength based on co-occurrence frequency.

        Args:
            relationships: List of relationships

        Returns:
            Dictionary mapping (source, target) pairs to interaction count
        """
        counts = defaultdict(int)

        for rel in relationships:
            if rel.rel_type == RelationType.INTERACTS_WITH:
                key = tuple(sorted([rel.source, rel.target]))
                counts[key] += 1

        return dict(counts)

    def merge_with_seed_data(
        self, extracted: List[Relationship]
    ) -> List[Relationship]:
        """
        Merge extracted relationships with seed data.

        Seed data takes precedence for known relationships.

        Args:
            extracted: List of extracted relationships

        Returns:
            Merged list of relationships
        """
        # Create lookup for seed relationships
        seed_lookup = {}
        for rel in self.seed_relationships:
            key = (rel.source, rel.target, rel.rel_type)
            seed_lookup[key] = rel

        # Merge: extracted relationships that aren't in seed data
        merged = list(self.seed_relationships)

        for rel in extracted:
            key = (rel.source, rel.target, rel.rel_type)
            reverse_key = (rel.target, rel.source, rel.rel_type)

            # Skip if already in seed data
            if key in seed_lookup or reverse_key in seed_lookup:
                continue

            merged.append(rel)

        return merged

    def extract_all_relations(
        self, extraction_result: ExtractionResult
    ) -> List[Relationship]:
        """
        Extract all relationships from an extraction result.

        Args:
            extraction_result: Result from entity extraction

        Returns:
            List of all extracted relationships
        """
        all_relations = []

        # 1. Co-occurrence relationships
        cooccurrence = self.extract_cooccurrence_relations(extraction_result.raw_text)
        all_relations.extend(cooccurrence)

        # 2. Dialogue pattern relationships
        dialogue_rels = self.extract_dialogue_relations(extraction_result.raw_text)
        all_relations.extend(dialogue_rels)

        # 3. Organization relationships
        org_rels = self.extract_organization_relations(
            extraction_result.characters, extraction_result.raw_text
        )
        all_relations.extend(org_rels)

        return all_relations


def get_seed_relationships() -> List[Relationship]:
    """Get all predefined seed relationships."""
    return SEED_RELATIONSHIPS


if __name__ == "__main__":
    # Test extraction
    from pathlib import Path

    extractor = EntityExtractor()
    rel_extractor = RelationExtractor()

    test_file = Path("Data/1600/chapter0_dialogue.txt")
    if test_file.exists():
        result = extractor.extract_from_file(test_file)
        relations = rel_extractor.extract_all_relations(result)

        print(f"Extracted {len(relations)} relationships:")
        for rel in relations[:20]:
            print(f"  {rel.source} --[{rel.rel_type.value}]--> {rel.target}")

        # Show interaction strength
        cooccur = rel_extractor.extract_cooccurrence_relations(result.raw_text)
        strength = rel_extractor.calculate_interaction_strength(cooccur)

        print(f"\nTop interactions by frequency:")
        for (s, t), count in sorted(strength.items(), key=lambda x: -x[1])[:10]:
            print(f"  {s} <-> {t}: {count}")
    else:
        print("Test file not found. Run from project root.")
