# ReAct Agent Development Guide

> Quick reference for query methods used to build the ReAct agent tools.

## 1. Environment

```bash
# Install dependencies
pip install -r src/requirements.txt

# Run Neo4j
docker-compose up -d neo4j (Port: 7687)

# Run Qdrant
docker run -p 6333:6333 qdrant/qdrant
```

## 2. Graph Search (Neo4j)

**Import**: `from src.graph.searcher import GraphSearcher`

| Method | Signature | Description |
|--------|-----------|-------------|
| **Fact Search** | `search(entity, relation=None, depth=1) -> Dict` | Find static facts. Supports alias resolution. |
| **History** | `search_history(entity, target=None) -> List[Dict]` | **Temporal**: Get relationship evolution over chapters. |
| **Path** | `get_path_between(e1, e2) -> Dict` | Find shortest connection path (max 4 hops). |
| **Friends** | `get_friends(char_name) -> List[Dict]` | Get characters with `FRIEND_OF` relation. |
| **Org** | `get_character_organization(char_name) -> List[Dict]` | Find tribe/faction membership (e.g., "MEMBER_OF"). |

**Example**:
```python
with GraphSearcher() as searcher:
    # 1. Who is Kinich?
    info = searcher.search("基尼奇")
    
    # 2. Relationship timeline with Mavuika
    timeline = searcher.search_history("基尼奇", "玛薇卡")
```

## 3. Vector Search (Qdrant)

**Import**: `from src.ingestion import VectorIndexer, EmbeddingGenerator`

| Method | Signature | Description |
|--------|-----------|-------------|
| **Semantic** | `search(query_vector, limit=5, filter_conditions=None)` | Find story chunks matching meaning. |
| **Filters** | `{"characters": "Name", "task_id": "ID", "chapter": int}` | Metadata filtering supported in `filter_conditions`. |

**Example**:
```python
embedder = EmbeddingGenerator()
indexer = VectorIndexer()

# Search for plot details mentioning Chasca
query_vec = embedder.embed_single("How did Chasca react to the contest?")
results = indexer.search(
    query_vector=query_vec,
    filter_conditions={"characters": "恰斯卡"},
    limit=5
)
```

## 4. Agent Tool Wrappers (Proposed)

| Tool Name | Purpose | Underlying API |
|-----------|---------|----------------|
| `lookup_knowledge(entity, relation)` | Static Facts | `GraphSearcher.search` |
| `search_memory(query, characters)` | Plot Details | `VectorIndexer.search` |
| `track_journey(entity)` | Timeline | `GraphSearcher.search_history` |

# Current Status

- Read files under docs/query/ and .project/case-ToolDesign/
- Consider: what query method should we add for our vector and graph database