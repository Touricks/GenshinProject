# Project Status Overview

> Generated: 2026-01-29
> Project: Genshin Story QA System (原神剧情问答系统)

## 1. Project Overview

**Status:** Design Complete / Implementation Ready
**Latest Versions:** PRD v1.2 | Tech Stack v1.2
**Objective:** Build a RAG-based question-answering system for Genshin Impact story queries with high retrieval accuracy and faithfulness.

---

## 2. Current Planning State

### 2.1 PRD & Requirements (Complete)

**Vision:** Enable players to quickly query and review game story content through natural language (solving "too much story to remember" problem)

**Three User Personas:**
- **Story Reviewers (Primary):** Casual/returning players wanting to recall prior story
- **Story Researchers (Secondary):** Content creators needing deep analysis of character relationships and event chains
- **Multi-turn Dialoguers (Tertiary):** Users exploring topics through follow-up questions

**Four Epic Feature Sets:**
1. **Epic 1:** Basic Factual Queries (character info, locations, events)
2. **Epic 2:** Relationship Queries (character relationships, org membership, associated entities)
3. **Epic 3:** Cross-Chapter Tracking (character development, event chains)
4. **Epic 4:** Multi-turn Dialogue (pronoun resolution, context continuation, topic switching)

**MVP Scope (v1.0):**
- Vector-based retrieval
- Basic multi-turn dialogue (simple history window)
- Streamlit Web UI
- Factual and simple relationship queries
- Basic evaluation framework

**Deferred (v2.0+):**
- Complex knowledge graph (Neo4j)
- Long-term memory (Mem0)
- Advanced multi-turn dialogue
- High-performance Web UI

---

## 3. Technical Architecture

### 3.1 Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **LLM** | Gemini 2.5 Pro | GCP free tier for students, strong Chinese understanding |
| **Embedding Model** | BAAI/bge-base-zh-v1.5 | SOTA Chinese embeddings, 768 dimensions, local deployment |
| **Vector DB** | Qdrant (Docker) | High-performance filtering, flexible Payload, self-hosted |
| **Graph DB** | Neo4j (v2.0+) | Complex relationship queries, optional in MVP |
| **RAG Framework** | LlamaIndex | Unified framework, built-in loop, flexible LLM switching |
| **Agent** | LlamaIndex FunctionAgent | Native Function Calling integration with Gemini |
| **Memory** | ChatMemoryBuffer (v1.0) → Mem0 (v3.0) | Session-based history escalating to persistent memory |
| **Web UI** | Streamlit (v1.0) → React (v3.0) | Fast MVP prototyping to production-grade UI |

### 3.2 Core Retrieval Tools

Four main tools for the Agent to use:

1. **T1: vector_search** - General vector retrieval with optional filters
2. **T2: graph_search** - Graph traversal starting from entities (v2.0+)
3. **T3: track_entity** - Temporal tracking of entity occurrences
4. **T4: stop** - Terminates retrieval, begins answer generation

---

## 4. Data Organization

### 4.1 Raw Data Overview

**Location:** `Data/`

**Total:** 16 task folders + 1 backup folder
- **Tasks 1500-1506:** Sumeru series (须弥系列) - 21 chapters total
- **Tasks 1600-1608:** Natlan series (纳塔系列) - 31 chapters total
- **Total Dialogue Data:** ~28,584 lines across 52 chapter files

### 4.2 Data Pipeline Design

**Chunking Strategy:** Scene-based semantic chunking (NOT fixed-size)
- **Delimiters:** `## scene_title`, `---`, `## options`
- **Max chunk:** 1500 characters
- **Min chunk:** 200 characters
- **Overlap:** 100 characters

**Metadata Schema (Chunk-level):**
```
task_id, task_name, chapter_number, chapter_name, series_name
scene_name, scene_order, chunk_order, event_order
characters: [list]
has_choice: boolean
```

### 4.3 Qdrant Collection Configuration

**Collection:** `genshin_story`
- **Vector Size:** 768 (BGE-base-zh dimension)
- **Distance:** COSINE
- **Payload Indexes:** task_id, chapter_number, characters, event_order

---

## 5. Implementation Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Data Validation & Environment Setup | Not Started |
| Phase 1 | Data Processing Pipeline | Not Started |
| Phase 2 | Evaluation Dataset Construction | Not Started |
| Phase 3 | Agent Implementation | Not Started |
| Phase 4 | Integration & Evaluation | Not Started |

### Next Step: Phase 1 - Data Processing Pipeline

1. **Document Loader** - Parse 52 chapter files, extract headers
2. **Scene Chunker** - Split by `##` scene markers
3. **Metadata Enricher** - Extract characters, compute event_order
4. **Embedding Generator** - Batch vectorize using BGE
5. **Vector Indexer** - Create Qdrant collection, upsert with payload

---

## 6. Evaluation Targets (MVP)

| Metric | Target |
|--------|--------|
| Faithfulness | ≥85% (no hallucinations) |
| Recall@5 | ≥80% (context retrieval accuracy) |
| Answer Relevancy | ≥80% (direct response to questions) |
| Response time P95 | <20 seconds |

---

## 7. Key Documents

| Document | Location |
|----------|----------|
| PRD | `docs/PRD.md` |
| System Architecture | `docs/design/system-architecture.md` |
| Data Pipeline Design | `docs/design/data-pipeline.md` |
| Data Model (Neo4j) | `docs/design/data-model.md` |
| Tool Design ADR | `docs/adr/ADR-006-tool-design.md` |
| Implementation Plan | `docs/project/implementation-plan.md` |
| Evaluation Dataset | `docs/testing/evaluation-dataset.md` |
