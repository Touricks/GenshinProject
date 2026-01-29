# Implementation Checklist (方案 A)

> **策略**: 数据处理 → 评估集构建 → Agent 实现
> **创建时间**: 2026-01-29
> **关联文档**: PRD.md, ADR-006, data-pipeline-design.md, evaluation-dataset-design.md

---

## Phase 0: 数据验证与环境准备 (预计 0.5 天)

### 0.1 源数据格式验证
- [ ] 检查 15 个任务文件夹格式一致性 (1500-1506, 1600-1608)
- [ ] 验证文件头解析 (任务名、章节名、系列名)
- [ ] 验证场景分隔符 (`##`) 存在且一致
- [ ] 统计数据量: 任务数、章节数、预估字符数

### 0.2 开发环境配置
- [ ] 创建 `pyproject.toml` / `requirements.txt`
- [ ] 安装核心依赖:
  ```
  llama-index-core>=0.11
  llama-index-llms-gemini
  llama-index-embeddings-huggingface
  qdrant-client
  neo4j
  ```
- [ ] 配置 `.env` (GOOGLE_API_KEY, QDRANT_URL)
- [ ] 启动 Qdrant Docker (`docker run -p 6333:6333 qdrant/qdrant`)

### 0.3 项目结构初始化
```
src/
├── ingestion/          # 数据处理 Pipeline
│   ├── __init__.py
│   ├── loader.py       # DocumentLoader
│   ├── chunker.py      # SceneChunker
│   ├── enricher.py     # MetadataEnricher
│   ├── embedder.py     # EmbeddingGenerator
│   └── indexer.py      # VectorIndexer
├── models/
│   ├── __init__.py
│   ├── document.py     # DocumentMetadata
│   └── chunk.py        # Chunk, ChunkMetadata
├── agent/              # Agent 实现 (Phase 3)
├── retrieval/          # 检索工具 (Phase 3)
└── scripts/
    ├── ingest.py       # CLI: python -m scripts.ingest
    └── validate.py     # 数据验证脚本
```

---

## Phase 1: 数据处理 Pipeline (预计 2-3 天)

### 1.1 Document Loader (loader.py)
- [ ] 实现 `parse_header()`: 解析文件头元数据
  - 任务名、章节号、章节名 (`^# (.+) - 第(\d+)章[：:](.+)$`)
  - 系列名 (`^# (.+第.+幕)$`)
  - 来源 URL (`^# 来源[：:](.+)$`)
- [ ] 实现 `extract_summary()`: 提取剧情简介
- [ ] 实现 `load_document()`: 返回 DocumentMetadata + 正文内容
- [ ] 单元测试: 测试 Data/1600/chapter0_dialogue.txt

### 1.2 Scene Chunker (chunker.py)
- [ ] 实现 `split_by_scenes()`: 按 `##` 分割场景
- [ ] 实现 `split_long_scene()`: 超长场景二次分割 (>1500 chars)
- [ ] 实现 `add_overlap()`: 添加 100 字符重叠
- [ ] 配置参数:
  ```python
  MAX_CHUNK_SIZE = 1500
  MIN_CHUNK_SIZE = 200
  OVERLAP_SIZE = 100
  ```
- [ ] 单元测试: 验证 chunk 大小在 200-1500 范围内

### 1.3 Metadata Enricher (enricher.py)
- [ ] 实现 `extract_characters()`: 提取角色列表 (`^(.+)：`)
- [ ] 实现 `compute_event_order()`: 计算全局顺序
  ```python
  event_order = chapter_number * 1000 + scene_order * 10 + chunk_order
  ```
- [ ] 实现 `detect_choices()`: 检测选项分支
- [ ] 定义核心角色列表 (MAIN_CHARACTERS)
- [ ] 单元测试: 验证角色提取和 event_order 计算

### 1.4 Embedding Generator (embedder.py)
- [ ] 加载 BGE-base-zh-v1.5 模型
  ```python
  HuggingFaceEmbedding(model_name="BAAI/bge-base-zh-v1.5", device="mps")
  ```
- [ ] 实现批量嵌入 (batch_size=64)
- [ ] 性能测试: 处理 1000 chunks 的时间

### 1.5 Vector Indexer (indexer.py)
- [ ] 创建 Qdrant Collection (genshin_story)
  ```python
  VectorParams(size=768, distance=Distance.COSINE)
  ```
- [ ] 创建 Payload 索引:
  - `task_id` (KEYWORD)
  - `chapter_number` (INTEGER)
  - `characters` (KEYWORD array)
  - `event_order` (INTEGER)
- [ ] 实现批量 upsert
- [ ] 验证: 简单向量搜索测试

### 1.6 Pipeline 集成
- [ ] 实现 `scripts/ingest.py` CLI:
  ```bash
  python -m scripts.ingest Data/ --collection genshin_story
  ```
- [ ] 运行完整 Pipeline
- [ ] 验证检查清单:
  - [ ] 所有文件成功解析
  - [ ] Chunk 数量统计
  - [ ] 检索测试 ("恰斯卡的性格")

---

## Phase 2: 评估数据集构建 (预计 1-2 天)

### 2.1 目录结构
```
evaluation/
├── datasets/
│   ├── factual_qa.json       # 50 条
│   ├── relationship_qa.json  # 30 条
│   ├── tracking_qa.json      # 20 条
│   ├── multiturn_qa.json     # 15 条 (sessions)
│   └── boundary_qa.json      # 10 条
└── golden_contexts/
```

### 2.2 Factual QA (factual_qa.json) - 50 条
- [ ] 角色信息类 (20 条): "X是谁？", "X的性格？"
- [ ] 地点信息类 (10 条): "花羽会是什么？"
- [ ] 事件概述类 (20 条): "空月之歌讲了什么？"
- 格式:
  ```json
  {
    "id": "fact_001",
    "question": "...",
    "ground_truth": "...",
    "category": "character_info|location|event",
    "golden_context": {"file": "...", "scene_header": "..."}
  }
  ```

### 2.3 Relationship QA (relationship_qa.json) - 30 条
- [ ] 人物关系类 (15 条): "A和B是什么关系？"
- [ ] 组织归属类 (10 条): "A属于哪个组织？"
- [ ] 关联角色类 (5 条): "A的朋友有谁？"
- 格式:
  ```json
  {
    "id": "rel_001",
    "question": "...",
    "ground_truth": "...",
    "relationship_triple": {"subject": "A", "relation": "friend_of", "object": "B"}
  }
  ```

### 2.4 Tracking QA (tracking_qa.json) - 20 条
- [ ] 事件演变类 (10 条): "秘源机兵袭击的完整经过？"
- [ ] 角色发展类 (10 条): "旅行者如何获得古名？"
- 格式:
  ```json
  {
    "id": "track_001",
    "question": "...",
    "ground_truth": "...",
    "timeline_milestones": ["事件1", "事件2", "..."],
    "context_hops": 3
  }
  ```

### 2.5 Multiturn QA (multiturn_qa.json) - 15 sessions
- [ ] 代词消解类 (8 条): "他/她/它做了什么？"
- [ ] 上下文延续类 (7 条): "后来怎么样了？"
- 格式:
  ```json
  {
    "id": "session_001",
    "conversation": [
      {"role": "user", "content": "基尼奇的龙伙伴叫什么？"},
      {"role": "assistant", "ground_truth": "阿尤"},
      {"role": "user", "content": "它在任务中做了什么？"},
      {"role": "assistant", "ground_truth": "..."}
    ]
  }
  ```

### 2.6 Boundary QA (boundary_qa.json) - 10 条
- [ ] 超范围问题 (5 条): "钢铁侠能打赢火神吗？"
- [ ] 不安全内容 (5 条): "如何修改游戏数据？"

---

## Phase 3: Agent 实现 (预计 2-3 天)

### 3.1 检索工具实现 (retrieval/)
- [ ] T1 `vector_search.py`:
  - Qdrant 向量检索
  - chapter_filter 支持
  - entity_filter 支持
- [ ] T2 `graph_search.py`:
  - Neo4j Cypher 查询 (或简化版: 基于 metadata 的关系推断)
  - 获取相关 Chunks
- [ ] T3 `track_entity.py`:
  - 按 entity 过滤
  - 按 event_order 排序
- [ ] T4 `stop`: 简单 pass 实现

### 3.2 FunctionTool 定义 (agent/tools.py)
- [ ] 4 个工具的 `FunctionTool.from_defaults()`
- [ ] 完善 docstring (LlamaIndex 自动提取参数描述)

### 3.3 Agent 实现 (agent/agent.py)
- [ ] System Prompt 编写 (见 ADR-006 Section 6.3)
- [ ] GenshinRetrievalAgent 类:
  ```python
  class GenshinRetrievalAgent:
      def __init__(self):
          self.llm = Gemini(model="models/gemini-2.5-flash")
          self.agent = FunctionAgent(tools=tools, llm=self.llm, ...)

      async def run(self, query: str) -> str: ...
      async def chat(self, query: str) -> str: ...
  ```
- [ ] ChatMemoryBuffer 配置 (多轮对话支持)

### 3.4 Agent 测试
- [ ] 单工具测试: 每个 FunctionTool 独立验证
- [ ] 简单查询测试: "玛拉妮的性格？"
- [ ] 关系查询测试: "恰斯卡和卡齐娜是什么关系？"
- [ ] 时序追踪测试: "旅行者如何获得古名？"
- [ ] 多轮对话测试: 代词消解

---

## Phase 4: 集成与评估 (预计 1-2 天)

### 4.1 评估脚本
- [ ] 实现 `scripts/evaluate.py`:
  ```bash
  python -m scripts.evaluate --dataset factual_qa.json
  ```
- [ ] 指标计算:
  - Recall@5 (目标 ≥ 80%)
  - Faithfulness (目标 ≥ 85%)
  - 响应时间 P95 (目标 < 20s)

### 4.2 Web UI (Streamlit)
- [ ] 基础聊天界面
- [ ] 来源引用展示
- [ ] 多轮对话支持

### 4.3 文档更新
- [ ] 更新 README.md
- [ ] 部署说明文档

---

## 依赖清单

```toml
[project]
dependencies = [
    # Core
    "llama-index-core>=0.11",
    "llama-index-llms-gemini",
    "llama-index-embeddings-huggingface",
    # Storage
    "qdrant-client",
    "neo4j",  # Phase 2+
    # Utils
    "python-dotenv",
    "pydantic",
    # Evaluation
    "ragas",  # Optional
    # UI
    "streamlit",
]
```

---

## 快速验证命令

```bash
# Phase 0: 验证数据格式
python -m scripts.validate Data/

# Phase 1: 运行 Pipeline
python -m scripts.ingest Data/ --collection genshin_story

# Phase 2: (手动构建评估集)

# Phase 3: Agent 测试
python -c "
from src.agent import GenshinRetrievalAgent
import asyncio
agent = GenshinRetrievalAgent()
print(asyncio.run(agent.run('玛拉妮的性格是什么？')))
"

# Phase 4: 评估
python -m scripts.evaluate --dataset evaluation/datasets/factual_qa.json
```

---

## 进度追踪

| Phase | 状态 | 完成度 | 备注 |
|-------|------|--------|------|
| Phase 0 | ⏳ 待开始 | 0% | |
| Phase 1 | ⏳ 待开始 | 0% | |
| Phase 2 | ⏳ 待开始 | 0% | |
| Phase 3 | ⏳ 待开始 | 0% | |
| Phase 4 | ⏳ 待开始 | 0% | |
