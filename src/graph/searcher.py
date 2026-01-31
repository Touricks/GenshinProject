"""
Graph search interface for the graph_search tool.

Provides query methods for retrieving entity relationships from Neo4j.
"""

import logging
from typing import List, Dict, Any, Optional
from .connection import Neo4jConnection

logger = logging.getLogger(__name__)


class GraphSearcher:
    """Query interface for the Neo4j knowledge graph."""

    # Query templates for common operations
    QUERY_TEMPLATES = {
        # Get all relationships for an entity
        "all_relations": """
            MATCH (a {name: $entity})-[r]-(b)
            RETURN
                a.name as source,
                type(r) as relation,
                b.name as target,
                labels(b)[0] as target_type,
                b.description as description,
                properties(r) as rel_properties
            LIMIT $limit
        """,
        # Get specific relationship type
        "specific_relation": """
            MATCH (a {name: $entity})-[r:$rel_type]-(b)
            RETURN
                a.name as source,
                type(r) as relation,
                b.name as target,
                labels(b)[0] as target_type,
                b.description as description,
                properties(r) as rel_properties
            LIMIT $limit
        """,
        # Get organization members
        "org_members": """
            MATCH (c:Character)-[r:MEMBER_OF]->(o:Organization {name: $entity})
            RETURN
                c.name as name,
                c.title as title,
                c.description as description,
                r.role as role
        """,
        # Get character's organization
        "char_organization": """
            MATCH (c:Character {name: $entity})-[r:MEMBER_OF]->(o:Organization)
            RETURN
                o.name as org_name,
                o.type as org_type,
                o.description as description,
                r.role as role
        """,
        # Get shortest path between two entities (Excluding generic Region nodes to avoid useless paths)
        "path_between": """
            MATCH path = shortestPath(
                (a {name: $entity1})-[*..4]-(b {name: $entity2})
            )
            WHERE none(n in nodes(path) WHERE n:Region OR n:Nation)
            RETURN
                [n in nodes(path) | n.name] as path_nodes,
                [r in relationships(path) | type(r)] as path_relations,
                length(path) as path_length
        """,
        # Get character friends
        "friends": """
            MATCH (c:Character {name: $entity})-[r:FRIEND_OF]-(friend:Character)
            RETURN
                friend.name as name,
                friend.description as description,
                r.strength as friendship_strength
        """,
        # Get character partners
        "partners": """
            MATCH (c:Character {name: $entity})-[r:PARTNER_OF]-(partner:Character)
            RETURN
                partner.name as name,
                partner.description as description,
                r.type as partnership_type
        """,
        # Get chunks mentioning a character
        "character_chunks": """
            MATCH (c:Character {name: $entity})-[:MENTIONED_IN]->(ch:Chunk)
            RETURN
                ch.chunk_id as chunk_id,
                ch.task_id as task_id,
                ch.chapter_number as chapter,
                ch.event_order as event_order
            ORDER BY ch.event_order
            LIMIT $limit
        """,
        # Get characters in a chunk
        "chunk_characters": """
            MATCH (c:Character)-[:MENTIONED_IN]->(ch:Chunk {chunk_id: $chunk_id})
            RETURN
                c.name as name,
                c.description as description
        """,
    }

    def __init__(self, connection: Optional[Neo4jConnection] = None):
        """
        Initialize the graph searcher.

        Args:
            connection: Neo4j connection (creates new one if not provided)
        """
        self.conn = connection or Neo4jConnection()

    def close(self):
        """Close the Neo4j connection."""
        self.conn.close()

    def search(
        self,
        entity: str,
        relation: Optional[str] = None,
        depth: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Search for entity relationships in the graph.

        This is the main interface for the graph_search tool.

        Args:
            entity: Entity name to search for
            relation: Optional specific relationship type to filter
            depth: Search depth (not fully implemented yet)
            limit: Maximum number of results

        Returns:
            Dictionary with 'entities' list and metadata
        """
        logger.info(f"[Neo4j] search: entity={entity}, relation={relation}, limit={limit}")

        if relation:
            # Search for specific relationship type
            results = self._search_specific_relation(entity, relation, limit)
        else:
            # Search for all relationships
            results = self._search_all_relations(entity, limit)

        logger.debug(f"[Neo4j] search result: {len(results)} relations found")

        return {
            "entity": entity,
            "relation_filter": relation,
            "entities": results,
            "count": len(results),
        }

    def _resolve_canonical_name(self, entity_name: str) -> str:
        """
        Resolve an entity name (or alias) to its canonical name using the fulltext index.
        Prioritizes nodes with populated aliases (Seed Characters) over raw extracted nodes.
        """
        # Try fulltext search on Character index (ADR-006)
        query = """
            CALL db.index.fulltext.queryNodes("entity_alias_index", $name)
            YIELD node, score
            RETURN node.name as name, node.aliases as aliases, score
            LIMIT 5
        """
        try:
            results = self.conn.execute(query, {"name": entity_name})

            # Strategy: Prefer nodes that have aliases (implies Seed/Main Character)
            # 1. Look for match with aliases
            for res in results:
                if res.get("aliases") and len(res["aliases"]) > 0:
                     return res["name"]

            # 2. Fallback to top score if score is high enough (e.g. > 0.8)
            # For now we accept any match returned by Lucene as better than nothing
            if results:
                 return results[0]["name"]

        except Exception:
            # Index might not exist or other error, fallback
            pass

        return entity_name

    def _search_all_relations(self, entity: str, limit: int) -> List[Dict[str, Any]]:
        """Search for all relationships of an entity."""
        canonical_name = self._resolve_canonical_name(entity)
        query = self.QUERY_TEMPLATES["all_relations"]
        return self.conn.execute(query, {"entity": canonical_name, "limit": limit})

    def _search_specific_relation(
        self, entity: str, relation: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Search for specific relationship type."""
        canonical_name = self._resolve_canonical_name(entity)

        # Build query dynamically
        query = f"""
            MATCH (a {{name: $entity}})-[r:{relation}]-(b)
            RETURN
                a.name as source,
                type(r) as relation,
                b.name as target,
                labels(b)[0] as target_type,
                b.description as description,
                properties(r) as rel_properties
            LIMIT $limit
        """
        return self.conn.execute(query, {"entity": canonical_name, "limit": limit})

    def search_history(
        self, entity: str, target: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relationship history (temporal evolution) for an entity.

        Args:
            entity: The main entity to track
            target: Optional target entity to filter history with

        Returns:
            List of relationship events sorted by time.
        """
        logger.info(f"[Neo4j] search_history: entity={entity}, target={target}")

        canonical_source = self._resolve_canonical_name(entity)
        canonical_target = self._resolve_canonical_name(target) if target else None

        filters = "WHERE a.name = $source"
        if canonical_target:
            filters += " AND b.name = $target"

        query = f"""
            MATCH (a)-[r]->(b)
            {filters}
            RETURN
                a.name as source,
                b.name as target,
                type(r) as relation,
                r.chapter as chapter,
                r.task_id as task_id,
                r.evidence as evidence
            ORDER BY r.chapter ASC, r.task_id ASC
        """

        params = {"source": canonical_source}
        if canonical_target:
            params["target"] = canonical_target

        results = self.conn.execute(query, params)
        logger.debug(f"[Neo4j] search_history result: {len(results)} events found")
        return results

    def get_organization_members(self, org_name: str) -> List[Dict[str, Any]]:
        """
        Get all members of an organization.

        Args:
            org_name: Organization name

        Returns:
            List of member information
        """
        query = self.QUERY_TEMPLATES["org_members"]
        return self.conn.execute(query, {"entity": org_name})

    def get_character_organization(self, char_name: str) -> List[Dict[str, Any]]:
        """
        Get organization(s) a character belongs to.

        Args:
            char_name: Character name

        Returns:
            List of organization information
        """
        query = self.QUERY_TEMPLATES["char_organization"]
        return self.conn.execute(query, {"entity": char_name})

    def get_path_between(
        self, entity1: str, entity2: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find shortest path between two entities.

        Args:
            entity1: First entity name
            entity2: Second entity name

        Returns:
            Path information or None if no path exists
        """
        logger.info(f"[Neo4j] get_path_between: {entity1} -> {entity2}")

        canonical_1 = self._resolve_canonical_name(entity1)
        canonical_2 = self._resolve_canonical_name(entity2)
        query = self.QUERY_TEMPLATES["path_between"]
        results = self.conn.execute(query, {"entity1": canonical_1, "entity2": canonical_2})
        result = results[0] if results else None

        if result:
            logger.debug(f"[Neo4j] path found: {result.get('path_nodes', [])}")
        else:
            logger.debug(f"[Neo4j] no path found between {entity1} and {entity2}")

        return result

    def get_friends(self, char_name: str) -> List[Dict[str, Any]]:
        """
        Get friends of a character.

        Args:
            char_name: Character name

        Returns:
            List of friend information
        """
        canonical_name = self._resolve_canonical_name(char_name)
        query = self.QUERY_TEMPLATES["friends"]
        return self.conn.execute(query, {"entity": canonical_name})

    def get_partners(self, char_name: str) -> List[Dict[str, Any]]:
        """
        Get partners of a character.

        Args:
            char_name: Character name

        Returns:
            List of partner information
        """
        canonical_name = self._resolve_canonical_name(char_name)
        query = self.QUERY_TEMPLATES["partners"]
        return self.conn.execute(query, {"entity": canonical_name})

    def get_character_chunks(
        self, char_name: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get chunks that mention a character.

        Args:
            char_name: Character name
            limit: Maximum number of chunks

        Returns:
            List of chunk information
        """
        canonical_name = self._resolve_canonical_name(char_name)
        query = self.QUERY_TEMPLATES["character_chunks"]
        return self.conn.execute(query, {"entity": canonical_name, "limit": limit})

    def get_chunk_characters(self, chunk_id: str) -> List[Dict[str, Any]]:
        """
        Get characters mentioned in a chunk.

        Args:
            chunk_id: Chunk identifier

        Returns:
            List of character information
        """
        query = self.QUERY_TEMPLATES["chunk_characters"]
        return self.conn.execute(query, {"chunk_id": chunk_id})

    def get_major_events(
        self,
        entity: str,
        event_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get major events experienced by a character.

        This method queries MajorEvent nodes connected via EXPERIENCES edges.
        It addresses the "abstract query vs concrete narrative" semantic gap:
        - User asks: "How did the girl return to the world?"
        - This returns: ["献出身体", "化作月光", ...] with summaries

        Args:
            entity: Character name (supports alias resolution)
            event_type: Optional filter by event type
                        (sacrifice/transformation/acquisition/loss/
                         encounter/conflict/revelation/milestone)
            limit: Maximum number of events to return

        Returns:
            List of event dicts sorted by chapter ASC, containing:
            - event_name: Name of the event
            - event_type: Type classification
            - chapter: Chapter number
            - summary: One-sentence summary
            - evidence: Original text evidence
            - role: Character's role (subject/object/witness)
            - outcome: Effect of the event
        """
        logger.info(
            f"[Neo4j] get_major_events: entity={entity}, event_type={event_type}"
        )

        canonical_name = self._resolve_canonical_name(entity)

        if event_type:
            query = """
                MATCH (c:Character {name: $entity})-[r:EXPERIENCES]->(e:MajorEvent)
                WHERE e.event_type = $event_type
                RETURN e.name as event_name,
                       e.event_type as event_type,
                       e.chapter as chapter,
                       e.task_id as task_id,
                       e.summary as summary,
                       e.evidence as evidence,
                       r.role as role,
                       r.outcome as outcome
                ORDER BY e.chapter ASC
                LIMIT $limit
            """
            results = self.conn.execute(
                query,
                {"entity": canonical_name, "event_type": event_type, "limit": limit},
            )
        else:
            query = """
                MATCH (c:Character {name: $entity})-[r:EXPERIENCES]->(e:MajorEvent)
                RETURN e.name as event_name,
                       e.event_type as event_type,
                       e.chapter as chapter,
                       e.task_id as task_id,
                       e.summary as summary,
                       e.evidence as evidence,
                       r.role as role,
                       r.outcome as outcome
                ORDER BY e.chapter ASC
                LIMIT $limit
            """
            results = self.conn.execute(
                query, {"entity": canonical_name, "limit": limit}
            )

        logger.debug(f"[Neo4j] get_major_events result: {len(results)} events found")
        return results

    def natural_language_query(self, question: str) -> Dict[str, Any]:
        """
        DEPRECATED: Use specific tools (e.g., search(), get_friends()) coupled with
        an LLM Agent instead of this rule-based router.

        Original Purpose: Process a natural language query about relationships.
        """
        raise NotImplementedError(
            "natural_language_query is deprecated. Please use specific API methods "
            "like search(), get_friends(), etc."
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


# Convenience function for tool integration
def graph_search(
    entity: str,
    relation: Optional[str] = None,
    depth: int = 1,
) -> Dict[str, Any]:
    """
    Graph search function for integration with RAG tools.

    Args:
        entity: Entity name to search for
        relation: Optional relationship type filter
        depth: Search depth

    Returns:
        Search results
    """
    with GraphSearcher() as searcher:
        return searcher.search(entity, relation, depth)


if __name__ == "__main__":
    # Test the searcher
    searcher = GraphSearcher()

    if searcher.conn.verify_connectivity():
        print("Testing GraphSearcher...")

        # Test 1: Search all relations for a character
        print("\n1. All relations for 恰斯卡:")
        result = searcher.search("恰斯卡")
        for entity in result["entities"][:5]:
            print(f"  {entity}")

        # Test 2: Search friends
        print("\n2. Friends of 恰斯卡:")
        friends = searcher.get_friends("恰斯卡")
        for friend in friends:
            print(f"  {friend['name']}: {friend.get('friendship_strength', 'unknown')}")

        # Test 3: Organization members
        print("\n3. Members of 花羽会:")
        members = searcher.get_organization_members("花羽会")
        for member in members:
            print(f"  {member['name']} ({member.get('role', 'member')})")

        # Test 4: Path between entities
        print("\n4. Path between 基尼奇 and 恰斯卡:")
        path = searcher.get_path_between("基尼奇", "恰斯卡")
        if path:
            print(f"  Path: {' -> '.join(path['path_nodes'])}")
            print(f"  Relations: {path['path_relations']}")

    else:
        print("Cannot connect to Neo4j. Make sure it's running.")

    searcher.close()
