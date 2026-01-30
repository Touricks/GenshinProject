# Vector Search API Reference

> Reference documentation for vector database methods available during ReAct Agent tool calls.

---

## Overview

When the LlamaIndex FunctionAgent executes tool calls, it can invoke the following vector search methods to retrieve relevant dialogue chunks from Qdrant.

---

## Core Classes

### 1. VectorIndexer

**Module**: `src.ingestion.indexer`

Primary class for interacting with Qdrant vector database.

```python
from src.ingestion import VectorIndexer

indexer = VectorIndexer(
    host: str = "localhost",      # Qdrant server host
    port: int = 6333,             # Qdrant server port
    collection_name: str = "genshin_story",  # Collection name
    vector_size: int = 768,       # Embedding dimension
)
```

---

### 2. EmbeddingGenerator

**Module**: `src.ingestion.embedder`

Generates query embeddings using BGE-base-zh-v1.5 model.

```python
from src.ingestion import EmbeddingGenerator

embedder = EmbeddingGenerator(
    model_name: str = "BAAI/bge-base-zh-v1.5",
    batch_size: int = 64,
    device: str = "auto",  # "auto", "cpu", "cuda", "mps"
)
```

---

### 3. JinaReranker

**Module**: `src.ingestion.reranker`

Reranks search results for improved relevance.

```python
from src.ingestion import JinaReranker

reranker = JinaReranker(
    model_name: str = "jinaai/jina-reranker-v2-base-multilingual",
    device: str = "auto",
    top_k: int = 5,
)
```

---

## Method Signatures

### VectorIndexer.search()

**Primary search method for ReAct tool calls.**

```python
def search(
    self,
    query_vector: List[float],
    limit: int = 5,
    filter_conditions: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query_vector` | `List[float]` | required | 768-dimensional embedding vector |
| `limit` | `int` | 5 | Maximum number of results |
| `filter_conditions` | `Dict[str, Any]` | None | Metadata filters (see below) |

**Returns:**

```python
[
    {
        "id": int,           # Point ID
        "score": float,      # Cosine similarity score (0-1)
        "payload": {
            "text": str,             # Dialogue text
            "task_id": str,          # e.g., "1600"
            "task_name": str,        # e.g., "归途"
            "chapter_number": int,   # e.g., 0
            "chapter_title": str,    # e.g., "墟火"
            "series_name": str,      # e.g., "空月之歌"
            "scene_title": str,
            "scene_order": int,
            "chunk_order": int,
            "event_order": int,      # Global temporal order
            "characters": List[str], # e.g., ["恰斯卡", "派蒙"]
            "has_choice": bool,
            "source_file": str,
        }
    },
    ...
]
```

**Filter Conditions:**

| Field | Type | Example |
|-------|------|---------|
| `task_id` | KEYWORD | `{"task_id": "1600"}` |
| `chapter_number` | INTEGER | `{"chapter_number": 0}` |
| `characters` | KEYWORD | `{"characters": "恰斯卡"}` |
| `event_order` | INTEGER | `{"event_order": 16000010}` |
| `series_name` | KEYWORD | `{"series_name": "空月之歌"}` |

---

### EmbeddingGenerator.embed_single()

**Generate embedding for a single query.**

```python
def embed_single(self, text: str) -> List[float]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Query text to embed |

**Returns:** `List[float]` - 768-dimensional embedding vector

---

### EmbeddingGenerator.embed_texts()

**Batch embedding for multiple texts.**

```python
def embed_texts(
    self,
    texts: List[str],
    show_progress: bool = True,
) -> List[List[float]]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `texts` | `List[str]` | required | List of texts to embed |
| `show_progress` | `bool` | True | Show progress bar |

**Returns:** `List[List[float]]` - List of 768-dimensional embeddings

---

### JinaReranker.rerank()

**Rerank documents by relevance to query.**

```python
def rerank(
    self,
    query: str,
    documents: List[str],
    top_k: int = None,
) -> Dict[str, Any]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | required | Search query |
| `documents` | `List[str]` | required | Document texts to rerank |
| `top_k` | `int` | 5 | Number of top results |

**Returns:**

```python
{
    "scores": List[float],    # Relevance scores (descending)
    "indices": List[int],     # Original indices of top documents
    "documents": List[str],   # Top document texts
}
```

---

### JinaReranker.rerank_with_metadata()

**Rerank search results preserving metadata.**

```python
def rerank_with_metadata(
    self,
    query: str,
    results: List[Dict[str, Any]],
    text_key: str = "text",
    top_k: int = None,
) -> List[Dict[str, Any]]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | required | Search query |
| `results` | `List[Dict]` | required | Search results from VectorIndexer |
| `text_key` | `str` | "text" | Key for text in payload |
| `top_k` | `int` | 5 | Number of top results |

**Returns:** `List[Dict[str, Any]]` - Reranked results with original metadata

---

## Usage in ReAct Agent

### Tool Definition (LlamaIndex FunctionTool)

```python
from llama_index.core.tools import FunctionTool

def vector_search(
    query: str,
    task_id: str = None,
    characters: str = None,
    limit: int = 5,
) -> str:
    """
    Search for relevant dialogue chunks in the story database.

    Args:
        query: Natural language search query
        task_id: Optional task ID filter (e.g., "1600")
        characters: Optional character name filter (e.g., "恰斯卡")
        limit: Maximum results to return

    Returns:
        Formatted search results with dialogue text and metadata
    """
    # 1. Generate embedding
    query_vector = embedder.embed_single(query)

    # 2. Build filters
    filters = {}
    if task_id:
        filters["task_id"] = task_id
    if characters:
        filters["characters"] = characters

    # 3. Vector search (over-fetch for reranking)
    results = indexer.search(
        query_vector=query_vector,
        limit=limit * 4,  # Over-fetch
        filter_conditions=filters or None,
    )

    # 4. Rerank
    reranked = reranker.rerank_with_metadata(query, results, top_k=limit)

    # 5. Format output
    return format_results(reranked)

# Create tool
vector_search_tool = FunctionTool.from_defaults(fn=vector_search)
```

### Example ReAct Flow

```
User: 少女为什么离开霜月之子？

Agent Thought: I need to search for information about why the girl left the Frost Moon Children.

Agent Action: vector_search(query="少女为什么离开霜月之子", limit=5)

Agent Observation:
1. [Task 1607, Ch2] 少女：嗯…那里，和我想象中不太一样。
   「木偶」：顺带一问，你想象中什么地方会让你想留下？
   少女：唔…不会向我索求我办不到的事情，不会敬仰我、畏惧我...

Agent Thought: The girl left because the Frost Moon Children expected too much from her as a deity. She wanted a place where people would treat her naturally without worship.

Agent Response: 少女离开霜月之子是因为那里"和她想象中不太一样"。作为月神，她不想被人索求做不到的事情，也不想被敬仰和畏惧。她渴望一个能让人自然地和她聊天、能自由出入的地方。
```

---

## Related Files

| File | Description |
|------|-------------|
| [src/ingestion/indexer.py](../../src/ingestion/indexer.py) | VectorIndexer implementation |
| [src/ingestion/embedder.py](../../src/ingestion/embedder.py) | EmbeddingGenerator implementation |
| [src/ingestion/reranker.py](../../src/ingestion/reranker.py) | JinaReranker implementation |
| [docs/design/ingestion.md](../design/ingestion.md) | Data pipeline design |
| [docs/design/system-architecture.md](../design/system-architecture.md) | System architecture |
