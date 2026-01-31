# Graph Database Incremental Modification API

> Internal documentation for Neo4j incremental write interfaces.

---

## Overview

The system uses **MERGE semantics** for all graph writes, enabling idempotent incremental updates. This document covers the write interfaces exposed by `GraphBuilder` and supporting extraction/merge components.

---

## Core Write Methods

### GraphBuilder Class

**Module**: `src/graph/builder.py`

#### 1. create_character()

Full character upsert with all properties.

```python
def create_character(
    self,
    name: str,
    aliases: List[str] = None,
    title: str = None,
    region: str = None,
    tribe: str = None,
    vision: str = None,
    weapon: str = None,
    affiliation: str = None,
    description: str = None,
) -> Optional[str]
```

**Cypher Pattern**:
```cypher
MERGE (c:Character {name: $name})
SET c.aliases = $aliases,
    c.title = $title,
    c.region = $region,
    c.tribe = $tribe,
    c.vision = $vision,
    c.weapon = $weapon,
    c.affiliation = $affiliation,
    c.description = $description
RETURN c.name as name
```

**Semantics**:
- MERGE on `name` (unique constraint)
- SET updates all properties on every call
- Idempotent: safe for repeated calls

---

#### 2. create_character_simple()

Lightweight character creation with first-appearance tracking.

```python
def create_character_simple(
    self,
    name: str,
    task_id: str = None,
    chapter_number: int = None,
) -> Optional[str]
```

**Cypher Pattern**:
```cypher
MERGE (c:Character {name: $name})
ON CREATE SET
    c.first_appearance_task = $task_id,
    c.first_appearance_chapter = $chapter
RETURN c.name as name
```

**Semantics**:
- MERGE on `name`
- **ON CREATE SET**: Only sets first-appearance on new nodes
- Subsequent calls preserve original first-appearance metadata

---

#### 3. create_relationship()

Create or update typed relationship between entities.

```python
def create_relationship(
    self,
    relationship: Relationship,
) -> Optional[str]
```

**Cypher Pattern**:
```cypher
MATCH (a:{source_label} {name: $source})
MATCH (b:{target_label} {name: $target})
MERGE (a)-[r:{rel_type}]->(b)
SET r.description = $description,
    r.strength = $strength,
    r.source_task = $source_task
RETURN type(r) as rel_type
```

**Semantics**:
- MATCH both endpoints first (must exist)
- MERGE creates relationship if new
- SET updates properties on existing
- Silently fails if endpoints don't exist

---

#### 4. Batch Methods

```python
def create_characters_batch(
    self,
    characters: Set[str],
    task_id: str = None,
    chapter_number: int = None,
) -> int

def create_relationships_batch(
    self,
    relationships: List[Relationship],
) -> int
```

**Semantics**:
- Sequential MERGE operations (not atomic)
- Each entity/relationship in its own transaction
- Returns count of successful operations

---

## Incremental Extraction Layer

### KGMerger Class

**Module**: `src/ingestion/incremental_extractor.py`

Deduplicates entities and relationships from multiple extraction outputs.

```python
class KGMerger:
    def __init__(self, alias_map: Dict[str, str] = None):
        """
        Args:
            alias_map: Maps aliases to canonical names
                       e.g., {"杜麦尼": "旅行者", "玩家": "旅行者"}
        """

    def normalize_name(self, name: str) -> str:
        """Convert alias to canonical form."""

    def merge(self, outputs: List[KnowledgeGraphOutput]) -> KnowledgeGraphOutput:
        """Merge multiple extractions into deduplicated output."""
```

**Deduplication Strategy**:

| Data Type | Key | Merge Behavior |
|-----------|-----|----------------|
| Entity | normalized name | Merge aliases, prefer non-null fields |
| Relationship | (source, target, type) | Keep first occurrence |

---

### IncrementalKGExtractor Class

Manages incremental extraction with file tracking.

```python
class IncrementalKGExtractor:
    def __init__(
        self,
        cache_dir: Path = None,
        tracking_file: Path = None,
    ):
        """Initialize with optional custom paths."""

    def get_changed_files(
        self,
        data_dir: Path,
        pattern: str = "**/chapter*_dialogue.txt",
    ) -> List[Path]:
        """Return files with changed content hash."""

    def extract_file(
        self,
        file_path: Path,
        force: bool = False,
    ) -> KnowledgeGraphOutput:
        """Extract KG from file (uses cache if available)."""

    def extract_incremental(
        self,
        data_dir: Path,
        pattern: str = "**/chapter*_dialogue.txt",
    ) -> KnowledgeGraphOutput:
        """Extract all files, using cache when possible, merge results."""
```

**File Tracking**:

```python
@dataclass
class FileTrackingInfo:
    file_path: str
    content_hash: str      # MD5 of file content
    last_processed: str    # ISO timestamp
    entity_count: int
    relationship_count: int
```

**Storage**: `.cache/kg/tracking.json`

---

## Snapshot Management

### KGSnapshotManager Class

**Module**: `src/ingestion/kg_snapshot.py`

```python
class KGSnapshotManager:
    def __init__(self, snapshot_dir: Path = None):
        """Default: .cache/kg/snapshots/"""

    def save(
        self,
        kg: KnowledgeGraphOutput,
        name: str = None,
        metadata: dict = None,
    ) -> Path:
        """Save timestamped snapshot."""

    def list_snapshots(self) -> List[Dict]:
        """List all snapshots, newest first."""

    def get_latest(self) -> Optional[KnowledgeGraphOutput]:
        """Load most recent snapshot."""

    def compare(
        self,
        snapshot1_path: Path,
        snapshot2_path: Path,
    ) -> Dict:
        """Diff two snapshots."""
```

**Snapshot Format**:
```json
{
  "version": "1.0",
  "created_at": "2026-01-29T22:00:00",
  "name": "after_extraction",
  "stats": {
    "entities": 150,
    "relationships": 200,
    "characters": 45
  },
  "metadata": {...},
  "kg": {...}
}
```

---

## Transaction Semantics

### Neo4j Write Wrapper

```python
# src/graph/connection.py
def execute_write(self, query: str, params: dict = None) -> List[dict]:
    """
    Execute write query in transaction.

    - Each call = one transaction
    - Auto-commit on success
    - Auto-rollback on exception
    """
```

### Batch Behavior

| Operation | Atomicity | On Failure |
|-----------|-----------|------------|
| Single MERGE | Atomic | Rollback |
| create_characters_batch() | Non-atomic | Continue to next |
| create_relationships_batch() | Non-atomic | Continue to next |

---

## Incremental Write Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Incremental Graph Update Workflow                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Change Detection                                         │
│     IncrementalKGExtractor.get_changed_files()              │
│     - Compare MD5 hashes against tracking.json              │
│     - Return list of new/modified files                     │
│                                                              │
│  2. Extraction (LLM or Cache)                               │
│     IncrementalKGExtractor.extract_file()                   │
│     - Check cache first (content hash key)                  │
│     - Call LLM extractor if not cached                      │
│     - Store result in cache                                 │
│                                                              │
│  3. Merge & Deduplicate                                     │
│     KGMerger.merge()                                        │
│     - Normalize aliases to canonical names                  │
│     - Deduplicate entities by name                          │
│     - Deduplicate relationships by (src, tgt, type)         │
│                                                              │
│  4. Graph Write                                              │
│     GraphBuilder.create_characters_batch()                  │
│     GraphBuilder.create_relationships_batch()               │
│     - MERGE semantics ensure idempotency                    │
│     - ON CREATE SET preserves first-appearance              │
│                                                              │
│  5. Update Tracking                                          │
│     IncrementalKGExtractor._save_tracking()                 │
│     - Save file hashes and stats                            │
│                                                              │
│  6. Snapshot (Optional)                                      │
│     KGSnapshotManager.save()                                │
│     - Timestamped backup for rollback                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Usage Examples

### Incremental Extraction + Graph Write

```python
from pathlib import Path
from src.ingestion.incremental_extractor import IncrementalKGExtractor
from src.graph.builder import GraphBuilder
from src.models.relationships import Relationship, RelationType

# Initialize
extractor = IncrementalKGExtractor()

# Extract incrementally
kg = extractor.extract_incremental(Path("Data/"))

# Write to Neo4j
with GraphBuilder() as builder:
    builder.setup_schema()
    # 1. Create Character nodes
    char_names = {e.name for e in kg.entities if e.entity_type == "Character"}
    builder.create_characters_batch(char_names)
    # 2. Convert ExtractedRelationship -> Relationship and create edges
    for rel in kg.relationships:
        relationship = Relationship(
            source=rel.source,
            target=rel.target,
            rel_type=RelationType[rel.relation_type],
            properties={"description": rel.description, "evidence": rel.evidence},
        )
        builder.create_relationship(relationship)
```

### Snapshot Before/After Comparison

```python
from src.ingestion.kg_snapshot import KGSnapshotManager

manager = KGSnapshotManager()

# Save before state
before_path = manager.save(kg_before, name="before_update")

# ... perform updates ...

# Save after state
after_path = manager.save(kg_after, name="after_update")

# Compare
diff = manager.compare(before_path, after_path)
print(f"New entities: {diff['entities_added']}")
print(f"Removed entities: {diff['entities_removed']}")
```

---

## Related Files

| File | Purpose |
|------|---------|
| [src/graph/builder.py](../src/graph/builder.py) | Neo4j write operations |
| [src/graph/connection.py](../src/graph/connection.py) | Database connection layer |
| [src/ingestion/incremental_extractor.py](../src/ingestion/incremental_extractor.py) | Incremental extraction + merge |
| [src/ingestion/kg_snapshot.py](../src/ingestion/kg_snapshot.py) | Snapshot management |
| [src/ingestion/kg_cache.py](../src/ingestion/kg_cache.py) | Content-based caching |
