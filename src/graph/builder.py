"""
Graph builder for constructing the Neo4j knowledge graph.

Provides methods to create nodes and relationships in Neo4j.
"""

from typing import List, Dict, Any, Optional, Set
from tqdm import tqdm

from .connection import Neo4jConnection
from ..models.entities import (
    Character,
    Organization,
    Location,
    Event,
    KNOWN_ORGANIZATIONS,
    MAIN_CHARACTERS,
)
from ..models.relationships import Relationship, RelationType, SEED_RELATIONSHIPS


class GraphBuilder:
    """Build and populate the Neo4j knowledge graph."""

    def __init__(self, connection: Optional[Neo4jConnection] = None):
        """
        Initialize the graph builder.

        Args:
            connection: Neo4j connection (creates new one if not provided)
        """
        self.conn = connection or Neo4jConnection()

    def close(self):
        """Close the Neo4j connection."""
        self.conn.close()

    # =========================================================================
    # Schema Setup
    # =========================================================================

    def create_constraints(self):
        """Create unique constraints for node types."""
        constraints = [
            "CREATE CONSTRAINT character_name IF NOT EXISTS FOR (c:Character) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT org_name IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
            "CREATE CONSTRAINT location_name IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
            "CREATE CONSTRAINT event_name IF NOT EXISTS FOR (e:Event) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (ch:Chunk) REQUIRE ch.chunk_id IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                self.conn.execute(constraint)
            except Exception as e:
                # Constraint may already exist
                print(f"Constraint warning: {e}")

    def create_indexes(self):
        """Create performance indexes."""
        indexes = [
            "CREATE INDEX character_region IF NOT EXISTS FOR (c:Character) ON (c.region)",
            "CREATE INDEX character_tribe IF NOT EXISTS FOR (c:Character) ON (c.tribe)",
            "CREATE INDEX chunk_event_order IF NOT EXISTS FOR (ch:Chunk) ON (ch.event_order)",
            "CREATE INDEX chunk_task IF NOT EXISTS FOR (ch:Chunk) ON (ch.task_id)",
            # Fulltext index for alias resolution (ADR-006)
            "CREATE FULLTEXT INDEX entity_alias_index IF NOT EXISTS FOR (c:Character) ON EACH [c.name, c.aliases]",
        ]

        for index in indexes:
            try:
                self.conn.execute(index)
            except Exception as e:
                print(f"Index warning: {e}")

    def setup_schema(self):
        """Set up all constraints and indexes."""
        print("Setting up Neo4j schema...")
        self.create_constraints()
        self.create_indexes()
        print("Schema setup complete.")

    # =========================================================================
    # Node Creation
    # =========================================================================

    def create_character(self, character: Character) -> None:
        """
        Create or update a Character node.

        Args:
            character: Character entity to create
        """
        query = """
        MERGE (c:Character {name: $name})
        SET c.aliases = $aliases,
            c.title = $title,
            c.region = $region,
            c.tribe = $tribe,
            c.description = $description,
            c.first_appearance_task = $first_appearance_task,
            c.first_appearance_chapter = $first_appearance_chapter
        RETURN c.name as name
        """
        self.conn.execute_write(query, character.to_dict())

    def create_organization(self, organization: Organization) -> None:
        """
        Create or update an Organization node.

        Args:
            organization: Organization entity to create
        """
        query = """
        MERGE (o:Organization {name: $name})
        SET o.type = $type,
            o.region = $region,
            o.description = $description
        RETURN o.name as name
        """
        self.conn.execute_write(query, organization.to_dict())

    def create_location(self, location: Location) -> None:
        """
        Create or update a Location node.

        Args:
            location: Location entity to create
        """
        query = """
        MERGE (l:Location {name: $name})
        SET l.type = $type,
            l.region = $region,
            l.description = $description
        RETURN l.name as name
        """
        self.conn.execute_write(query, location.to_dict())

    def create_event(self, event: Event) -> None:
        """
        Create or update an Event node.

        Args:
            event: Event entity to create
        """
        query = """
        MERGE (e:Event {name: $name})
        SET e.type = $type,
            e.chapter_range = $chapter_range,
            e.description = $description
        RETURN e.name as name
        """
        self.conn.execute_write(query, event.to_dict())

    def create_character_simple(
        self,
        name: str,
        task_id: Optional[str] = None,
        chapter: Optional[int] = None,
    ) -> None:
        """
        Create a simple Character node with just the name.

        Used for characters discovered during extraction that aren't in seed data.

        Args:
            name: Character name
            task_id: First appearance task ID
            chapter: First appearance chapter number
        """
        query = """
        MERGE (c:Character {name: $name})
        ON CREATE SET
            c.first_appearance_task = $task_id,
            c.first_appearance_chapter = $chapter
        RETURN c.name as name
        """
        self.conn.execute_write(
            query, {"name": name, "task_id": task_id, "chapter": chapter}
        )

    # =========================================================================
    # Relationship Creation
    # =========================================================================

    def create_relationship(self, relationship: Relationship) -> None:
        """
        Create a relationship between two entities.

        Args:
            relationship: Relationship to create
        """
        # Build property SET clause dynamically
        props = relationship.properties.copy()
        
        # Add temporal properties if present
        if relationship.chapter is not None:
            props["chapter"] = relationship.chapter
        if relationship.task_id:
            props["task_id"] = relationship.task_id

        prop_sets = ", ".join([f"r.{k} = ${k}" for k in props.keys()])

        # Determine source and target labels based on relationship type
        source_label, target_label = self._get_labels_for_relationship(
            relationship.rel_type
        )

        if "chapter" in props:
             # Temporal relationship: unique by type AND chapter
            query = f"""
            MATCH (a:{source_label} {{name: $source}})
            MATCH (b:{target_label} {{name: $target}})
            MERGE (a)-[r:{relationship.rel_type.value} {{chapter: $chapter}}]->(b)
            {"SET " + prop_sets if prop_sets else ""}
            RETURN type(r) as rel_type
            """
        else:
            # Static relationship: unique by type only
            query = f"""
            MATCH (a:{source_label} {{name: $source}})
            MATCH (b:{target_label} {{name: $target}})
            MERGE (a)-[r:{relationship.rel_type.value}]->(b)
            {"SET " + prop_sets if prop_sets else ""}
            RETURN type(r) as rel_type
            """

        params = {"source": relationship.source, "target": relationship.target, **props}

        try:
            self.conn.execute_write(query, params)
        except Exception as e:
            # May fail if nodes don't exist - that's OK for some relationships
            pass

    def _get_labels_for_relationship(
        self, rel_type: RelationType
    ) -> tuple[str, str]:
        """
        Determine node labels based on relationship type.

        Args:
            rel_type: Type of relationship

        Returns:
            Tuple of (source_label, target_label)
        """
        if rel_type in [
            RelationType.FRIEND_OF,
            RelationType.ENEMY_OF,
            RelationType.PARTNER_OF,
            RelationType.FAMILY_OF,
            RelationType.INTERACTS_WITH,
        ]:
            return "Character", "Character"
        elif rel_type == RelationType.MEMBER_OF:
            # Could be Character->Organization or Organization->Organization
            return "Character", "Organization"
        elif rel_type == RelationType.LEADER_OF:
            return "Character", "Organization"
        elif rel_type == RelationType.PARTICIPATED_IN:
            return "Character", "Event"
        elif rel_type == RelationType.OCCURRED_AT:
            return "Event", "Location"
        elif rel_type == RelationType.MENTIONED_IN:
            return "Character", "Chunk"
        elif rel_type == RelationType.CONTAINS:
            return "Event", "Chunk"
        else:
            # Default: try Character to Character
            return "Character", "Character"

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def create_seed_organizations(self) -> None:
        """Create all known organizations from seed data."""
        print("Creating seed organizations...")
        for org in KNOWN_ORGANIZATIONS.values():
            self.create_organization(org)
        print(f"  Created {len(KNOWN_ORGANIZATIONS)} organizations.")

    def create_seed_characters(self) -> None:
        """Create all known characters from seed data."""
        print("Creating seed characters...")
        for char in MAIN_CHARACTERS.values():
            self.create_character(char)
        print(f"  Created {len(MAIN_CHARACTERS)} characters.")

    def create_seed_relationships(self) -> None:
        """Create all relationships from seed data."""
        print("Creating seed relationships...")
        for rel in tqdm(SEED_RELATIONSHIPS, desc="  Relationships"):
            self.create_relationship(rel)
        print(f"  Created {len(SEED_RELATIONSHIPS)} relationships.")

    def create_characters_batch(
        self,
        characters: Set[str],
        task_id: Optional[str] = None,
        chapter: Optional[int] = None,
    ) -> None:
        """
        Create multiple character nodes in batch.

        Args:
            characters: Set of character names
            task_id: Task ID for first appearance
            chapter: Chapter number for first appearance
        """
        for name in characters:
            # Skip if it's a known character (already created with full data)
            if name in MAIN_CHARACTERS:
                continue
            self.create_character_simple(name, task_id, chapter)

    def create_relationships_batch(self, relationships: List[Relationship]) -> None:
        """
        Create multiple relationships in batch.

        Args:
            relationships: List of relationships to create
        """
        for rel in relationships:
            self.create_relationship(rel)

    # =========================================================================
    # Chunk Integration (Phase 5)
    # =========================================================================

    def create_chunk(
        self,
        chunk_id: str,
        event_order: int,
        task_id: str,
        chapter_number: int,
        characters: List[str],
    ) -> None:
        """
        Create a Chunk node and link it to characters.

        Args:
            chunk_id: Unique chunk identifier (matches Qdrant)
            event_order: Temporal ordering value
            task_id: Task ID the chunk belongs to
            chapter_number: Chapter number
            characters: List of characters mentioned in the chunk
        """
        # Create chunk node
        create_query = """
        MERGE (ch:Chunk {chunk_id: $chunk_id})
        SET ch.event_order = $event_order,
            ch.task_id = $task_id,
            ch.chapter_number = $chapter_number
        RETURN ch.chunk_id as id
        """
        self.conn.execute_write(
            create_query,
            {
                "chunk_id": chunk_id,
                "event_order": event_order,
                "task_id": task_id,
                "chapter_number": chapter_number,
            },
        )

        # Link to characters
        link_query = """
        MATCH (ch:Chunk {chunk_id: $chunk_id})
        MATCH (c:Character {name: $char_name})
        MERGE (c)-[:MENTIONED_IN]->(ch)
        """
        for char_name in characters:
            try:
                self.conn.execute_write(
                    link_query, {"chunk_id": chunk_id, "char_name": char_name}
                )
            except Exception:
                pass  # Character may not exist

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def clear_graph(self) -> None:
        """Delete all nodes and relationships. USE WITH CAUTION."""
        query = "MATCH (n) DETACH DELETE n"
        self.conn.execute_write(query)
        print("Graph cleared.")

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the current graph."""
        queries = {
            "characters": "MATCH (c:Character) RETURN count(c) as count",
            "organizations": "MATCH (o:Organization) RETURN count(o) as count",
            "locations": "MATCH (l:Location) RETURN count(l) as count",
            "events": "MATCH (e:Event) RETURN count(e) as count",
            "chunks": "MATCH (ch:Chunk) RETURN count(ch) as count",
            "relationships": "MATCH ()-[r]->() RETURN count(r) as count",
        }

        stats = {}
        for name, query in queries.items():
            result = self.conn.execute(query)
            stats[name] = result[0]["count"] if result else 0

        return stats

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
