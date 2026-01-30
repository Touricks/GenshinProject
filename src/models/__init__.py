"""
Data models for the Genshin Story QA System.

This module provides dataclasses for:
- Entities: Character, Organization, Location, Event
- Relationships: Relationship, RelationType
- Documents: DocumentMetadata, RawDocument
- Chunks: Chunk, ChunkMetadata
"""

from .entities import (
    Character,
    Organization,
    Location,
    Event,
    KNOWN_ORGANIZATIONS,
    MAIN_CHARACTERS,
    SYSTEM_CHARACTERS,
)
from .relationships import (
    Relationship,
    RelationType,
    SEED_RELATIONSHIPS,
    RELATIONSHIP_KEYWORDS,
)
from .document import DocumentMetadata, RawDocument
from .chunk import Chunk, ChunkMetadata

__all__ = [
    # Entities
    "Character",
    "Organization",
    "Location",
    "Event",
    "KNOWN_ORGANIZATIONS",
    "MAIN_CHARACTERS",
    "SYSTEM_CHARACTERS",
    # Relationships
    "Relationship",
    "RelationType",
    "SEED_RELATIONSHIPS",
    "RELATIONSHIP_KEYWORDS",
    # Documents
    "DocumentMetadata",
    "RawDocument",
    # Chunks
    "Chunk",
    "ChunkMetadata",
]
