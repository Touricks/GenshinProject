# Genshin Story QA - Source Code

This directory contains the core modules for the Genshin Story QA system.

## Directory Structure

```
src/
├── config/          # Configuration and settings
├── graph/           # Neo4j graph database operations
├── ingestion/       # Data ingestion and KG extraction
├── models/          # Entity and relationship models
├── query/           # Query processing (vector + graph)
├── scripts/         # Utility scripts
└── .env             # Environment configuration
```

---

## Knowledge Graph Extraction

### Overview

The system supports two extraction methods:
1. **Regex-based** (fast, limited accuracy ~35%)
2. **LLM-based** (slower, high accuracy ~85%+) - **Recommended**

LLM extraction uses Gemini via OpenAI-compatible API for complete KG extraction including:
- Entities: Characters, Organizations, Locations
- Relationships: KNOWS, WORKS_WITH, MEMBER_OF, etc.
- Attributes: Roles (医生), aliases (杜麦尼→旅行者)

---

## Quick Start

### 1. Environment Setup

Create `src/.env`:
```env
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# LLM API (Gemini)
GEMINI_API_KEY=AIzaSy...
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-2.0-flash
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Usage Guide

### Initial KG Extraction (Full Processing)

Extract KG from all dialogue files and load to Neo4j:

```python
from pathlib import Path
from ingestion import IncrementalKGExtractor, KGSnapshotManager
from graph import GraphBuilder

# Step 1: Extract KG from all dialogue files
extractor = IncrementalKGExtractor()
merged_kg = extractor.extract_all(Path("../Data"), force=True)

print(f"Extracted: {len(merged_kg.entities)} entities, {len(merged_kg.relationships)} relationships")

# Step 2: Save snapshot before loading to Neo4j
snapshot_manager = KGSnapshotManager()
snapshot_path = snapshot_manager.save(merged_kg, name="initial_extraction")
print(f"Snapshot saved: {snapshot_path}")

# Step 3: Load to Neo4j
with GraphBuilder() as builder:
    # Setup schema
    builder.setup_schema()

    # Create entity nodes
    for entity in merged_kg.entities:
        if entity.entity_type == "Character":
            builder.create_character_simple(entity.name)
        # Add more entity types as needed

    # Create relationships
    from models.relationships import Relationship, RelationType
    for rel in merged_kg.relationships:
        try:
            rel_type = RelationType[rel.relation_type]
            relationship = Relationship(
                source=rel.source,
                target=rel.target,
                rel_type=rel_type,
            )
            builder.create_relationship(relationship)
        except KeyError:
            pass  # Unknown relationship type

    # Print stats
    stats = builder.get_stats()
    print(f"Neo4j Stats: {stats}")
```

### Incremental Update (Changed Files Only)

Only process files that have changed since last extraction:

```python
from pathlib import Path
from ingestion import IncrementalKGExtractor

extractor = IncrementalKGExtractor()

# Check what files have changed
changed = extractor.get_changed_files(Path("../Data"))
print(f"Changed files: {len(changed)}")

# Incremental extraction (uses cache for unchanged files)
merged_kg = extractor.extract_incremental(Path("../Data"))

# View extraction status
status = extractor.get_status()
print(f"Tracked files: {status['tracked_files']}")
print(f"Cache stats: {status['cache_stats']}")
```

### Version Control with Snapshots

Manage KG versions for backup and comparison:

```python
from pathlib import Path
from ingestion import KGSnapshotManager, IncrementalKGExtractor

# Create snapshot manager
manager = KGSnapshotManager()

# Save current KG state
extractor = IncrementalKGExtractor()
merged_kg = extractor.extract_incremental(Path("../Data"))
path = manager.save(merged_kg, name="v1.0")
print(f"Saved snapshot: {path}")

# List all snapshots
for snap in manager.list_snapshots():
    print(f"  [{snap['name']}] {snap['entities']} entities, {snap['relationships']} rels")

# Load latest snapshot
latest_kg = manager.get_latest()

# Load specific snapshot by name
kg_v1 = manager.get_by_name("v1.0")

# Compare two snapshots
if len(manager.list_snapshots()) >= 2:
    snapshots = manager.list_snapshots()
    comparison = manager.compare(Path(snapshots[0]['path']), Path(snapshots[1]['path']))
    print(f"Entities only in snapshot 1: {comparison['entities']['only_in_1']}")
    print(f"Entities only in snapshot 2: {comparison['entities']['only_in_2']}")
```

---

## Module Reference

### ingestion/

| Class | Purpose |
|-------|---------|
| `LLMKnowledgeGraphExtractor` | LLM-based entity/relationship extraction |
| `KnowledgeGraphOutput` | Pydantic model for extraction results |
| `ExtractedEntity` | Entity with name, type, role, aliases |
| `ExtractedRelationship` | Relationship with source, target, type |
| `KGCache` | MD5-based caching for extraction results |
| `CachedKGExtractor` | Extractor with transparent caching |
| `IncrementalKGExtractor` | Incremental extraction with change tracking |
| `KGMerger` | Merge multiple KGs with deduplication |
| `KGSnapshotManager` | Versioned KG snapshots |

### graph/

| Class | Purpose |
|-------|---------|
| `Neo4jConnection` | Database connection management |
| `GraphBuilder` | Create nodes and relationships |
| `GraphSearcher` | Query the graph for QA |

---

## Workflow Examples

### Workflow 1: First-Time Setup

```bash
# 1. Start Neo4j
docker-compose up -d neo4j

# 2. Extract and load
python -c "
from pathlib import Path
from ingestion import IncrementalKGExtractor, KGSnapshotManager
from graph import GraphBuilder

# Extract
extractor = IncrementalKGExtractor()
kg = extractor.extract_all(Path('../Data'))

# Save snapshot
KGSnapshotManager().save(kg, name='initial')

# Load to Neo4j
with GraphBuilder() as builder:
    builder.setup_schema()
    builder.create_seed_organizations()
    builder.create_seed_characters()
    for entity in kg.entities:
        if entity.entity_type == 'Character':
            builder.create_character_simple(entity.name)
    print(builder.get_stats())
"
```

### Workflow 2: Daily Update

```bash
python -c "
from pathlib import Path
from ingestion import IncrementalKGExtractor, KGSnapshotManager

extractor = IncrementalKGExtractor()
changed = extractor.get_changed_files(Path('../Data'))

if changed:
    print(f'Processing {len(changed)} changed files...')
    kg = extractor.extract_incremental(Path('../Data'))
    KGSnapshotManager().save(kg, name='daily_update')
else:
    print('No changes detected')
"
```

### Workflow 3: Rollback to Previous Version

```python
from pathlib import Path
from ingestion import KGSnapshotManager

manager = KGSnapshotManager()

# List available snapshots
for snap in manager.list_snapshots():
    print(f"{snap['created_at']}: {snap['name']} ({snap['entities']} entities)")

# Load a specific version
old_kg = manager.get_by_name("v1.0")
# Then reload to Neo4j...
```

---

## Cache and Storage

### Cache Location

```
.cache/kg/
├── tracking.json      # File change tracking
├── <md5_hash>.json    # Cached extraction results
└── snapshots/
    ├── initial_20260129_120000.json
    └── v1.0_20260129_150000.json
```

### Cache Management

```python
from ingestion import KGCache, IncrementalKGExtractor

# View cache stats
cache = KGCache()
print(cache.get_stats())

# Clear cache (forces re-extraction)
cache.clear()

# Clear tracking only (keeps cache)
extractor = IncrementalKGExtractor()
extractor.clear_tracking()
```

---

## Configuration

### Entity Alias Normalization

The `KGMerger` automatically normalizes entity names:

| Alias | Canonical Name |
|-------|----------------|
| 杜麦尼 | 旅行者 |
| 玩家 | 旅行者 |
| Traveler | 旅行者 |

Add custom aliases:

```python
from ingestion import KGMerger

merger = KGMerger()
merger.add_alias("应急食品", "派蒙")
merger.add_alias("小派", "派蒙")
```

---

## Testing

```bash
# Run all extraction tests (no LLM required)
pytest tests/extraction/ -v -m "not llm"

# Run with LLM tests (requires API key)
pytest tests/extraction/ -v

# Test specific module
pytest tests/extraction/graph/test_incremental.py -v
```

---

## Troubleshooting

### LLM API Errors

```python
# Test LLM connection
from llama_index.llms.openai_like import OpenAILike
import os
from dotenv import load_dotenv

load_dotenv("src/.env")
llm = OpenAILike(
    model=os.getenv("GEMINI_MODEL"),
    api_base=os.getenv("GEMINI_BASE_URL"),
    api_key=os.getenv("GEMINI_API_KEY"),
    is_chat_model=True,
)
print(llm.complete("Hello"))
```

### Neo4j Connection Issues

```python
# Test Neo4j connection
from graph import Neo4jConnection

conn = Neo4jConnection()
result = conn.execute("RETURN 1 as test")
print(result)
conn.close()
```

### Cache Corruption

```bash
# Reset cache completely
rm -rf .cache/kg/
```
