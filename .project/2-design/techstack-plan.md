# Tech Stack Plan: Genshin Story QA System

> 版本: 1.2
> 创建日期: 2026-01-27
> 状态: Decision-Finalized Draft

---

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     Web UI (Streamlit)                      │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  RAG Engine │  │ ReAct Agent │  │   ChatMemoryBuffer  │ │
│  │ (LlamaIndex)│  │(FunctionAgent)│ │  (LlamaIndex)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                      Storage Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Qdrant    │  │   Neo4j     │  │    SQLite/Redis     │ │
│  │ (Vectors)   │  │  (v2.0+)    │  │   (Session/Cache)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                      Model Layer                            │
│  ┌─────────────┐  ┌─────────────────────────────────────┐  │
│  │Gemini 2.5   │  │ BAAI/bge-base-zh-v1.5 (Embedding)   │  │
│  │(via LlamaIndex)│ │ + Jina Reranker (Local)           │  │
│  └─────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 版本演进路线

| Layer | Component | MVP (v1.0) | v2.0 | v3.0 | Notes |
|-------|-----------|------------|------|------|-------|
| **LLM** | Generation | Gemini 3 Pro | Gemini 3 Pro | Gemini 3 Pro | GCP 学生免费额度，中文能力强 |
| **Embedding** | Vectorization | bge-base-zh-v1.5 | bge-base-zh-v1.5 | bge-large-zh-v1.5 | 本地部署，无 API 依赖 |
| **Vector DB** | Retrieval | Qdrant (Docker) | Qdrant | Qdrant | 开源自托管，性能优秀 |
| **Graph DB** | Relationships | - | Neo4j Community | Neo4j | 复杂关系查询 |
| **RAG Framework** | Orchestration | LlamaIndex | LlamaIndex | LlamaIndex | 成熟生态，灵活扩展 |
| **Memory** | Conversation | Sliding Window (Session DB) | Sliding Window | Mem0ai | 指代消解、会话上下文 |
| **Web UI** | Frontend | Streamlit | Streamlit | React | 快速原型 → 生产级 |
| **Evaluation** | Testing | RAGAS | RAGAS | RAGAS | 标准 RAG 评估框架 |

---

## 3. 组件选型详述

### 3.1 LLM 选型

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Gemini 3 Pro** | GCP 学生免费额度，中文理解强 | API 依赖 | ✅ **Primary** |
| GPT-4o | 广泛使用，工具生态丰富 | 成本较高 | Backup |
| Qwen2.5-72B | 本地部署，无 API 费用 | 需要 GPU 资源 | Offline backup |

**选择理由:**
- GCP 学生免费额度，MVP 阶段零成本
- 中文理解能力强，适合处理原神剧情的复杂表述

### 3.2 Embedding Model

| Option | Dimension | 中文性能 | 速度 | Recommendation |
|--------|-----------|----------|------|----------------|
| **bge-base-zh-v1.5** | 768 | SOTA | 快 | ✅ **MVP** |
| bge-large-zh-v1.5 | 1024 | Better | 中 | v3.0 升级 |
| text-embedding-3-small | 1536 | Good | 快 | API 备选 |

**选择理由:**
- BAAI BGE 系列是中文 Embedding 领域的 SOTA
- 本地部署，无 API 费用，无网络延迟
- base 版本在性能和速度之间取得良好平衡

### 3.3 Vector Database

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Qdrant** | 高性能过滤，Payload 灵活，自托管 | 相对较新 | ✅ Selected |
| Chroma | 简单易用，Python 原生 | 大规模性能较弱 | 快速原型备选 |
| Milvus | 企业级，分布式 | 过于复杂 | Overkill for this scale |

**选择理由:**
- 支持复杂的 Payload Filter（章节、任务、分支等元数据过滤）
- Docker 部署简单，资源占用低
- REST API 和 gRPC 双协议支持
- 与 LlamaIndex 集成良好

### 3.4 Agent Framework

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **LlamaIndex FunctionAgent** | 统一框架，内置 loop，易切换 LLM | 调试需 verbose=True | ✅ Selected |
| Gemini Native Functions | 格式稳定，原生支持 | 需自建 Loop (~100行) | Previous choice |
| LangChain Agents | 生态丰富 | 抽象过重 | Not recommended |

**选择理由:**
- 采用 **LlamaIndex FunctionAgent** (ADR-006 v2)
- 统一 Indexing 和 Agent 框架，减少代码量
- 内置 `ChatMemoryBuffer` 支持多轮对话和代词消解
- 易于切换 LLM Provider (Gemini ↔ Claude fallback)
- 与 Qdrant、Neo4j 均有官方集成

### 3.5 Graph Database (v2.0+)

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Neo4j Community** | 成熟稳定，Cypher 查询强大 | 内存占用较大 | ✅ Selected |
| LlamaIndex PropertyGraph | 轻量，与框架集成 | 功能有限 | MVP 替代方案 |
| NetworkX | Python 原生 | 仅内存，无持久化 | 原型验证 |

**选择理由:**
- 角色关系、事件脉络天然适合图结构
- Cypher 查询语言表达力强
- 社区版免费，满足项目规模

### 3.6 Reranker

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Jina Reranker v2** | 多语言支持(100+)，本地部署，轻量(~1.1GB) | 相对新 | ✅ Selected |
| BGE-Reranker-base | 中文优化 | 仅中英文 | 备选 |
| Cohere Rerank | 效果好 | API 依赖，成本 | 不符合本地需求 |

**选择理由:**
- `jina-reranker-v2-base-multilingual` 支持中文
- 本地部署，无 API 成本
- 显著提升 Precision，延迟可控 (~100-200ms)

### 3.7 Memory System (v3.0)

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **LangChain Logic** | 简单直接，适合 Session Context | 需要自行管理持久化 | ✅ Selected |
| Mem0 | 长期用户画像优秀 | 增加依赖，当前场景 Overkill | Deferred |
| LlamaIndex ChatMemory | 框架绑定 | 灵活性一般 | Backup |

**选择理由:**
- 当前核心需求是"多轮对话中的代词消解" (Short-term Context)
- 不需要复杂的跨 Session 用户偏好记忆
- 使用类似 LangChain 的 `ChatMessageHistory` 模式 (SQLite/Redis) 即可满足 Requirement

---

## 4. MVP (v1.0) 技术栈详细配置

```yaml
# 运行时环境
runtime:
  python: "3.11"
  package_manager: "uv"

# 核心组件
core:
  llm:
    primary:
      provider: "google"
      model: "gemini-3-pro"
      temperature: 0.1  # 降低随机性，提高 Faithfulness
    fallback:
      provider: "anthropic"
      model: "claude-sonnet-4-20250514"
  embedding:
    model: "BAAI/bge-base-zh-v1.5"
    device: "mps"  # Apple M4 Pro MPS 加速
    batch_size: 64  # M4 Pro 24GB 可支持较大 batch
  reranker:
    model: "jinaai/jina-reranker-v2-base-multilingual"
    device: "mps"
    top_k: 5  # Rerank 后保留 Top-5
  framework:
    name: "llama-index"
    version: ">=0.11"
    packages:
      - "llama-index-core>=0.11"
      - "llama-index-llms-gemini"
      - "llama-index-embeddings-huggingface"

# 存储层
storage:
  vector_db:
    type: "qdrant"
    deployment: "docker"
    port: 6333
    collection: "genshin_story"
  session:
    type: "sqlite"
    path: "./data/sessions.db"

# 用户界面
ui:
  web:
    framework: "streamlit"
    version: ">=1.35"
    port: 8501

# 评测框架
evaluation:
  framework: "ragas"
  metrics:
    - "faithfulness"
    - "answer_relevancy"
    - "context_recall"
    - "context_precision"

# 开发工具
dev_tools:
  testing: "pytest"
  linting: "ruff"
  typing: "pyright"
  formatting: "black"
```

---

## 5. 关键设计决策点

### 5.1 已确定的技术决策

| # | Decision | 选择 | Rationale |
|---|----------|------|-----------|
| D1 | **Embedding 部署方式** | Local HF | 无额外成本，低延迟 |
| D2 | **Qdrant 部署方式** | Docker | MVP 阶段易于管理 |
| D3 | **Chunking 策略** | Semantic | 对话类内容必须保持上下文 |
| D4 | **Query Rewriting** | 启用 | 中文问法多样，提升召回率 |
| D5 | **Hybrid Search** | Dense + BM25 | 角色名等关键词精确匹配 |
| D6 | **Reranker** | Jina Reranker v2 | 多语言支持，本地部署，提升 Precision |

### 5.2 核心架构决策

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 数据存储位置 | 本地 | PRD 要求无外传 |
| 主 LLM | Gemini 3 Pro | GCP 学生免费额度 |
| Fallback LLM | Claude Sonnet 4 | 备用，应对特殊场景 |
| 中文 Embedding | BGE-base-zh-v1.5 | 中文 SOTA，本地部署 |
| Reranker | Jina Reranker v2 | 多语言，本地部署 |
| RAG 框架 | LlamaIndex | 模块化 + 生态 |
| Sparse Retrieval | BM25 | Hybrid Search 标准配置 |

---

## 6. 数据流设计

### 6.1 索引流程 (Offline)

```
Raw Data (JSON/HTML)
        ↓
   Data Cleaning
   (去除系统提示、非剧情文本)
        ↓
   Semantic Chunking
   (基于对话轮次，保持上下文)
        ↓
   Context Injection
   (Header Propagation: 注入章节/场景标题)
        ↓
   Metadata Extraction
   (章节、任务、角色、分支ID/Scenario Tags)
        ↓
   Embedding Generation
   (bge-base-zh-v1.5)
        ↓
   Vector Storage
   (Qdrant with Payload)
```

### 6.2 查询流程 (Online) - LlamaIndex FunctionAgent

```
User Query
    ↓
ChatMemoryBuffer
(自动管理对话历史 + 代词消解)
    ↓
LlamaIndex FunctionAgent (内置 ReAct Loop)
    ↻ Thought: Analyze Query & Context
    ↻ Action: Call FunctionTools (Vector/Graph/Track)
    ↻ Observation: Receive Tool Outputs
    (Repeat 1-5 turns, max_function_calls=5)
    ↓
Final Answer Generation
(由 FunctionAgent 自动合成)
```

---

## 7. 资源估算

### 7.1 存储需求

| 组件 | 估算数据量 | 存储空间 |
|------|------------|----------|
| 原始数据 | ~18 任务 × ~60 章节 | ~50 MB |
| Chunks | ~5,000-10,000 个 | ~20 MB |
| Vectors (768d) | ~10,000 × 768 × 4 bytes | ~30 MB |
| Qdrant Index | 上述 + 元数据 | ~100 MB |
| **Total** | - | **~200 MB** |

### 7.2 计算需求 (MVP)

| 组件 | 最低配置 | 推荐配置 | 当前配置 ✅ |
|------|----------|----------|-------------|
| CPU | 4 cores | 8 cores | 12 cores (M4 Pro) |
| RAM | 8 GB | 16 GB | 24 GB |
| GPU/MPS | 不需要 | Optional | MPS 可用 |
| Disk | 10 GB | 20 GB | 197 GB |

### 7.3 API 成本估算 (Monthly)

| 使用场景 | 估算调用量 | 成本 (Gemini 3 Pro) |
|----------|------------|----------------------|
| 开发测试 | ~1,000 queries | $0 (GCP 免费额度) |
| 评测运行 | ~500 queries | $0 (GCP 免费额度) |
| 日常使用 | ~2,000 queries | $0 (GCP 免费额度) |
| **Total** | - | **$0/月** (学生额度内) |

> 注：GCP 学生账户免费额度足够覆盖 MVP 阶段使用。超出额度后按需评估是否切换到 Claude Fallback。

---

## 8. 待确认问题

1. **部署环境**: ✅ 已确认
   - [x] 本地开发机：Apple M4 Pro, 12 cores (8P+4E), 24GB RAM
   - [x] 磁盘空间：197GB 可用

2. **API Access**:
   - [x] ~~Claude API Key~~ → 使用 GCP 学生免费额度 (Gemini 3 Pro)
   - [ ] GCP 项目尚未配置 → 见 [setup-requirements.md](./setup-requirements.md)

3. **数据规模确认**:
   - [ ] ~18 任务 ~60 章节，预估 chunk 数量 5000-10000，是否准确？
   - [ ] 是否有后续大规模数据扩展计划？

4. **GPU 可用性**: ✅ 已确认
   - [x] Apple M4 Pro 支持 MPS 加速
   - [x] PyTorch 待安装，MPS 可用

5. **开发优先级**:
   - [ ] 是否需要先做技术 Spike 验证关键组件？
   - [ ] 评测数据集是否已准备好？ → 见 [setup-requirements.md](./setup-requirements.md)

---

## 10. 下一步

1. **确认上述待确认问题**
2. **创建 ADR 文档**（Architecture Decision Records）
3. **技术 Spike**：验证 Embedding + Qdrant + Claude 端到端流程
4. **进入 3-backend 开始实现**

---

## 9. Development Timeline

Based on the ReAct design (ADR-006), the development is divided into 4 phases:

| Phase | Duration | Goals | Key Deliverables |
|-------|----------|-------|------------------|
| **Phase 1: Foundation** | 3 Days | Environment & Skeleton | - Gemini API Wrapper with Token Bucket<br>- Basic Agent Loop (Mock Tools)<br>- Qdrant & Neo4j Docker Setup |
| **Phase 2: Tools Implementation** | 4 Days | Core Retrieval Tools | - T1: `vector_search` (with Qdrant filters)<br>- T2: `graph_search` (Cypher queries)<br>- T3: `track_entity` (Temporal sorting) |
| **Phase 3: Integration** | 3 Days | Agent Logic & State | - Session Context Manager (LangChain-style Hist)<br>- Prompt Engineering for Thought generation<br>- Connect Tools to live DBs |
| **Phase 4: Optimization** | 4 Days | Testing & Tuning | - Multi-turn conversation tests<br>- Latency optimization<br>- Error handling & Fallbacks |

**Total Estimated Duration**: ~2 Weeks

---

## 10. 下一步

- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [BGE Embedding Models](https://huggingface.co/BAAI/bge-base-zh-v1.5)
- [Jina Reranker v2](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual)
- [Google Gemini API](https://ai.google.dev/gemini-api/docs)
- [RAGAS Evaluation Framework](https://docs.ragas.io/)
- [LangChain Memory Documentation](https://python.langchain.com/docs/modules/memory/)
