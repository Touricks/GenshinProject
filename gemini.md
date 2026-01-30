# Gemini Agent Context & Roadmap

> **Role**: Primary Developer & Architect for Genshin QA System
> **Current Phase**: Tool Design & MVP Foundation (Post-ADR-006)
> **Last Update**: 2026-01-30

## 1. Project Overview
**Goal**: Build a RAG-based QA system for Genshin Impact story lore, featuring:
- **Dual Retrieval**: Vector (Semantic) + Graph (Reasoning/Relationships).
- **ReAct Agent**: LlamaIndex `FunctionAgent` for complex query orchestration.
- **Local First**: Runs on Apple Silicon (MPS), no external API dependencies (except Gemini/Claude fallback).

## 2. Current Architecture State
**Source of Truth**: `docs_internal/plan/0130-1521.md` & `docs/design/system-architecture.md`

- **LLM**: Gemini 3 Pro (Primary) / Claude Sonnet 4 (Fallback)
- **Embedding**: `BAAI/bge-base-zh-v1.5` (Local MPS)
- **Vector DB**: Qdrant (Docker) - Content & Dialogue
- **Graph DB**: Neo4j (Docker) - Entity Relationships
- **Reranker**: `jina-reranker-v2-base-multilingual`

## 3. Immediate roadmap (MVP)

### Phase 1: Foundation (Current)
- [ ] **Environment Setup**: Verify Gemini API wrapper, Token Bucket, and Docker services (Neo4j/Qdrant).
- [ ] **Agent Loop**: Implement basic LlamaIndex FunctionAgent loop.

### Phase 2: Core Tool Implementation
- [ ] **`vector_search`**: Implement Qdrant search with metadata filters (Task ID, Characters).
- [ ] **`graph_search`**: Implement Neo4j Cypher queries for facts and relationships.
- [ ] **`track_entity`**: Implement temporal event tracking (Order by Chapter).

### Phase 3: Integration & Memory
- [ ] **Session Memory**: Implement `ChatMemoryBuffer` (LangChain-style) for coreference resolution.
- [ ] **ReAct Logic**: Connect tools to valid DB instances.

## 4. Key References for Development
- **Plan**: `docs_internal/plan/0130-1521.md` (Main Roadmap)
- **Query APIs**: `docs/query/` (Tool Signatures)
- **PRD**: `docs/prd.md` (User Stories & Requirements)
- **Design**: `docs/design/system-architecture.md` (Tech Stack)

## 5. Next Actions
1. **Refactor Searcher**: Remove legacy hardcoded checks in `src/graph/searcher.py`.
2. **Implement Tools**: Build the specific tool functions defined in `docs/query/README.md`.
