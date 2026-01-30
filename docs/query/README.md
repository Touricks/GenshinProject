# Query Documentation

> API reference for retrieval tools used by the ReAct Agent.

---

## Documents

| Document | Description |
|----------|-------------|
| [vector-search-api.md](./vector-search-api.md) | Vector database (Qdrant) methods and signatures |
| [graph-search-api.md](./graph-search-api.md) | Knowledge graph (Neo4j) query methods |

---

## Dual Retrieval Architecture

The system uses two complementary retrieval systems:

```
User Query
    ├──→ Vector Search (semantic)
    │       ↓
    │    EmbeddingGenerator.embed_single(query)
    │       ↓
    │    VectorIndexer.search(query_vector, filters)
    │       ↓
    │    JinaReranker.rerank(query, results)
    │       ↓
    │    Dialogue Text Chunks
    │
    └──→ Graph Search (structured)
            ↓
         GraphSearcher.search(entity, relation)
            ↓
         Entity Relationships
            ↓
         Combined Results → Agent
```

---

## Key Components

### Vector Search (Qdrant)

| Component | Purpose | Latency |
|-----------|---------|---------|
| `EmbeddingGenerator` | Query → 768-dim vector | ~10ms |
| `VectorIndexer` | Vector similarity search | ~20-50ms |
| `JinaReranker` | Cross-encoder reranking | ~100-200ms |

### Graph Search (Neo4j)

| Component | Purpose | Latency |
|-----------|---------|---------|
| `Neo4jConnection` | Database connection pool | ~5ms |
| `GraphSearcher` | Relationship queries | ~10-30ms |

---

## When to Use Each

| Query Type | Use | Example |
|------------|-----|---------|
| Semantic search | Vector | "为什么少女离开了霜月之子？" |
| Relationships | Graph | "恰斯卡属于哪个部族？" |
| Character info | Graph | "基尼奇的朋友有谁？" |
| Dialogue retrieval | Vector | "关于火之意志的对话" |
| Path finding | Graph | "派蒙和玛薇卡是怎么认识的？" |

---

## Related

- [System Architecture](../design/system-architecture.md)
- [Data Pipeline](../design/ingestion.md)
- [ADR-006: Tool Design](../adr/ADR-006-tool-design.md)
