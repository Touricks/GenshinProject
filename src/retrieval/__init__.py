"""
Retrieval tools for the ReAct Agent.

This module provides 5 orthogonal tools following the Graph-Vector Complementarity design:

Graph Tools (Neo4j - fast, structured, no long text):
- lookup_knowledge: Static facts and direct relationships
- find_connection: Path finding between entities
- track_journey: Temporal evolution of relationships
- get_character_events: Major events and turning points (MajorEvent nodes)

Vector Tool (Qdrant - slower, returns story text):
- search_memory: Episodic memory, dialogue, plot details

Design Principle:
- Graph = Skeleton & Index (structure, logic, relationships)
- Vector = Flesh & Content (semantics, dialogue, episodes)
- Never store long text in Graph. Never derive relationships from Vector.
"""

from .lookup_knowledge import lookup_knowledge
from .find_connection import find_connection
from .track_journey import track_journey
from .search_memory import search_memory
from .get_character_events import get_character_events

__all__ = [
    "lookup_knowledge",
    "find_connection",
    "track_journey",
    "search_memory",
    "get_character_events",
]
