# Graph Search API Reference

> Reference documentation for Neo4j knowledge graph query methods available during ReAct Agent tool calls.

---

## Overview

The Neo4j knowledge graph stores structured relationship data about characters, organizations, locations, and events. The `GraphSearcher` class provides methods to query this graph for entity relationships, organizational memberships, and connection paths.

---

## Core Classes

### 1. Neo4jConnection

**Module**: `src.graph.connection`

Connection manager for Neo4j database with driver pooling and session management.

```python
from src.graph.connection import Neo4jConnection

conn = Neo4jConnection(
    uri: str = "bolt://localhost:7687",   # Neo4j Bolt URI
    user: str = "neo4j",                   # Username
    password: str = "genshin_story_qa",    # Password
)
```

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Database username |
| `NEO4J_PASSWORD` | `genshin_story_qa` | Database password |

---

### 2. GraphSearcher

**Module**: `src.graph.searcher`

Primary query interface for the knowledge graph.

```python
from src.graph.searcher import GraphSearcher

searcher = GraphSearcher(
    connection: Optional[Neo4jConnection] = None  # Uses default if not provided
)
```

---

## Graph Schema

### Node Types

| Label | Description | Key Properties |
|-------|-------------|----------------|
| `Character` | Story characters | `name`, `title`, `region`, `tribe`, `description`, `aliases` |
| `Organization` | Tribes, guilds, nations | `name`, `type`, `region`, `description` |
| `Location` | Places and landmarks | `name`, `type`, `region`, `description` |
| `Event` | Quests, battles, ceremonies | `name`, `type`, `chapter_range`, `description` |
| `Chunk` | Text segments linked to vector DB | `chunk_id`, `task_id`, `chapter_number`, `event_order` |

### Relationship Types

| Type | Direction | Description | Properties |
|------|-----------|-------------|------------|
| `FRIEND_OF` | bidirectional | Friendship between characters | `strength` |
| `PARTNER_OF` | bidirectional | Partnership (dragon partner, companion) | `type` |
| `MEMBER_OF` | Character → Organization | Organizational membership | `role` |
| `LEADER_OF` | Character → Organization | Leadership position | - |
| `MENTIONED_IN` | Character → Chunk | Character appears in text chunk | - |
| `ENEMY_OF` | bidirectional | Antagonistic relationship | `reason`, `resolved` |
| `FAMILY_OF` | bidirectional | Family relationship | - |

---

## Method Signatures

### GraphSearcher.search()

**Primary search method for ReAct tool calls.**

```python
def search(
    self,
    entity: str,
    relation: Optional[str] = None,
    depth: int = 1,
    limit: int = 20,
) -> Dict[str, Any]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity` | `str` | required | Entity name to search for |
| `relation` | `str` | None | Optional relationship type filter (e.g., "FRIEND_OF") |
| `depth` | `int` | 1 | Search depth (reserved for future use) |
| `limit` | `int` | 20 | Maximum number of results |

**Returns:**

```python
{
    "entity": str,           # Searched entity name
    "relation_filter": str,  # Applied filter (or None)
    "entities": [            # List of related entities
        {
            "source": str,           # Source entity name
            "relation": str,         # Relationship type
            "target": str,           # Target entity name
            "target_type": str,      # Target node type (Character, Organization, etc.)
            "description": str,      # Target description
            "rel_properties": dict,  # Relationship properties
        },
        ...
    ],
    "count": int,            # Number of results
}
```

**Example:**

```python
result = searcher.search("恰斯卡")
# Returns all relationships involving 恰斯卡

result = searcher.search("恰斯卡", relation="FRIEND_OF")
# Returns only friendships
```

---

### GraphSearcher.get_friends()

**Get friends of a character.**

```python
def get_friends(self, char_name: str) -> List[Dict[str, Any]]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `char_name` | `str` | Character name |

**Returns:**

```python
[
    {
        "name": str,                # Friend's name
        "description": str,         # Friend's description
        "friendship_strength": str, # "close" or "acquaintance"
    },
    ...
]
```

---

### GraphSearcher.get_partners()

**Get partners of a character (dragon partners, travel companions).**

```python
def get_partners(self, char_name: str) -> List[Dict[str, Any]]
```

**Returns:**

```python
[
    {
        "name": str,            # Partner's name
        "description": str,     # Partner's description
        "partnership_type": str # "dragon_partner", "travel_companion", etc.
    },
    ...
]
```

---

### GraphSearcher.get_organization_members()

**Get all members of an organization.**

```python
def get_organization_members(self, org_name: str) -> List[Dict[str, Any]]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `org_name` | `str` | Organization name (e.g., "花羽会") |

**Returns:**

```python
[
    {
        "name": str,        # Member's name
        "title": str,       # Member's title
        "description": str, # Member's description
        "role": str,        # Role in organization ("leader", "member", "elder")
    },
    ...
]
```

---

### GraphSearcher.get_character_organization()

**Get organization(s) a character belongs to.**

```python
def get_character_organization(self, char_name: str) -> List[Dict[str, Any]]
```

**Returns:**

```python
[
    {
        "org_name": str,     # Organization name
        "org_type": str,     # Organization type
        "description": str,  # Organization description
        "role": str,         # Character's role in organization
    },
    ...
]
```

---

### GraphSearcher.get_path_between()

**Find shortest path between two entities (max 4 hops).**

```python
def get_path_between(
    self,
    entity1: str,
    entity2: str,
) -> Optional[Dict[str, Any]]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entity1` | `str` | First entity name |
| `entity2` | `str` | Second entity name |

**Returns:**

```python
{
    "path_nodes": List[str],      # Entity names in path order
    "path_relations": List[str],  # Relationship types between nodes
    "path_length": int,           # Number of hops
}
# Returns None if no path exists
```

**Example:**

```python
path = searcher.get_path_between("基尼奇", "恰斯卡")
# Returns: {
#     "path_nodes": ["基尼奇", "竞人族", "恰斯卡"],
#     "path_relations": ["MEMBER_OF", "MEMBER_OF"],
#     "path_length": 2
# }
```

---

### GraphSearcher.get_character_chunks()

**Get text chunks that mention a character (links to vector DB).**

```python
def get_character_chunks(
    self,
    char_name: str,
    limit: int = 50,
) -> List[Dict[str, Any]]
```

**Returns:**

```python
[
    {
        "chunk_id": str,       # Chunk identifier (for vector DB lookup)
        "task_id": str,        # Task ID
        "chapter": int,        # Chapter number
        "event_order": int,    # Temporal ordering
    },
    ...
]
```

---

### GraphSearcher.get_chunk_characters()

**Get characters mentioned in a specific chunk.**

```python
def get_chunk_characters(self, chunk_id: str) -> List[Dict[str, Any]]
```

**Returns:**

```python
[
    {
        "name": str,        # Character name
        "description": str, # Character description
    },
    ...
]
```

---

### Neo4jConnection.execute()

**Execute arbitrary Cypher queries.**

```python
def execute(
    self,
    query: str,
    params: Optional[Dict[str, Any]] = None,
    database: str = "neo4j",
) -> List[Dict[str, Any]]
```

**Example:**

```python
# Custom query
results = conn.execute(
    "MATCH (c:Character) WHERE c.region = $region RETURN c.name",
    {"region": "纳塔"}
)
```

---

## Convenience Function

### graph_search()

**Standalone function for tool integration.**

```python
from src.graph.searcher import graph_search

def graph_search(
    entity: str,
    relation: Optional[str] = None,
    depth: int = 1,
) -> Dict[str, Any]
```

Automatically manages connection lifecycle (opens and closes).

---

## Usage in ReAct Agent

### Tool Definition (LlamaIndex FunctionTool)

```python
from llama_index.core.tools import FunctionTool
from src.graph.searcher import GraphSearcher

def graph_search_tool(
    entity: str,
    relation: str = None,
) -> str:
    """
    Search the knowledge graph for entity relationships.

    Args:
        entity: Entity name to search for (character, organization, etc.)
        relation: Optional relationship filter (FRIEND_OF, MEMBER_OF, PARTNER_OF, etc.)

    Returns:
        Formatted relationship information
    """
    with GraphSearcher() as searcher:
        if relation == "friends":
            results = searcher.get_friends(entity)
        elif relation == "organization":
            results = searcher.get_character_organization(entity)
        elif relation == "members":
            results = searcher.get_organization_members(entity)
        else:
            results = searcher.search(entity, relation)["entities"]

        return format_graph_results(results)

# Create tool
graph_tool = FunctionTool.from_defaults(fn=graph_search_tool)
```

### Example ReAct Flow

```
User: 恰斯卡属于哪个部族？

Agent Thought: I need to find what organization Chasca belongs to.

Agent Action: graph_search_tool(entity="恰斯卡", relation="organization")

Agent Observation:
- Organization: 花羽会
  Type: 部族
  Role: member
  Description: 纳塔六大部族之一，花羽会族人是...

Agent Thought: Chasca is a member of the Flower Feather Tribe (花羽会).

Agent Response: 恰斯卡属于花羽会，是纳塔六大部族之一。
```

### Combining with Vector Search

```python
def hybrid_search(query: str, entity: str) -> str:
    """
    Combine graph relationships with vector search results.
    """
    # 1. Get entity relationships
    with GraphSearcher() as searcher:
        relations = searcher.search(entity)

    # 2. Get relevant text chunks
    query_vector = embedder.embed_single(query)
    chunks = indexer.search(
        query_vector=query_vector,
        filter_conditions={"characters": entity},
        limit=5
    )

    # 3. Combine results
    return format_hybrid_results(relations, chunks)
```

---

## Cypher Query Examples

### Get all characters from a tribe

```cypher
MATCH (c:Character)-[:MEMBER_OF]->(o:Organization {name: "花羽会"})
RETURN c.name, c.title, c.description
```

### Find common connections between two characters

```cypher
MATCH (a:Character {name: "恰斯卡"})-[r1]-(common)-[r2]-(b:Character {name: "基尼奇"})
RETURN common.name, type(r1), type(r2)
```

### Get character interaction frequency

```cypher
MATCH (c1:Character {name: "派蒙"})-[:MENTIONED_IN]->(chunk:Chunk)<-[:MENTIONED_IN]-(c2:Character)
WHERE c2.name <> "派蒙"
RETURN c2.name, count(chunk) as co_appearances
ORDER BY co_appearances DESC
LIMIT 10
```

---

## Related Files

| File | Description |
|------|-------------|
| [src/graph/connection.py](../../src/graph/connection.py) | Neo4jConnection implementation |
| [src/graph/searcher.py](../../src/graph/searcher.py) | GraphSearcher implementation |
| [src/graph/builder.py](../../src/graph/builder.py) | GraphBuilder for data import |
| [docs/query/vector-search-api.md](./vector-search-api.md) | Vector database query reference |
| [.project/2-design/neo4j-schema-design.md](../../.project/2-design/neo4j-schema-design.md) | Full schema design |
