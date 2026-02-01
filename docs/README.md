# Genshin Story QA System - Documentation

> 文档导航页 | Documentation Hub

## Quick Links

| 文档类型 | 路径 | 说明 |
|----------|------|------|
| 产品需求 | [PRD.md](./PRD.md) | Product Requirements Document |
| 系统设计 | [design/](./design/) | Technical Design Documents |
| 架构决策 | [adr/](./adr/) | Architecture Decision Records |
| 项目管理 | [project/](./project/) | Implementation Plans |
| 测试文档 | [testing/](./testing/) | Evaluation & Testing |
| 查询 API | [query/](./query/) | Vector Search API Reference |

---

## 文档结构 (Google Style)

```
docs/
├── README.md                          # 本文件 - 导航页
├── PRD.md                             # 产品需求文档
│
├── design/                            # 设计文档 (Design Docs)
│   ├── README.md                      # 设计概览
│   ├── system-architecture.md         # 系统架构 & 技术选型
│   ├── ingestion.md                   # 数据处理流水线设计
│   └── data-model.md                  # 数据模型 (Neo4j Schema)
│
├── adr/                               # 架构决策记录 (ADRs)
│   ├── README.md                      # ADR 索引
│   └── ADR-006-tool-design.md         # 检索工具设计决策
│
├── project/                           # 项目管理
│   └── implementation-plan.md         # 实施计划 & 任务分解
│
├── query/                             # 查询 API 文档
│   ├── README.md                      # API 概览
│   └── vector-search-api.md           # Vector Search API Reference
│
└── testing/                           # 测试文档
    └── evaluation-dataset.md          # 评估数据集设计
```

---

## 文档生命周期

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Documentation Lifecycle                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: Planning          Phase 2: Design           Phase 3: Build        │
│  ─────────────────          ──────────────           ─────────────          │
│                                                                             │
│  ┌─────────┐               ┌─────────────────┐       ┌─────────────────┐   │
│  │  PRD    │ ────────────► │  Design Docs    │ ────► │ Implementation  │   │
│  │         │               │  + ADRs         │       │ Plan            │   │
│  └─────────┘               └─────────────────┘       └─────────────────┘   │
│       │                           │                          │              │
│       │                           │                          │              │
│       └───────────────────────────┴──────────────────────────┘              │
│                                   │                                         │
│                                   ▼                                         │
│                          ┌─────────────────┐                                │
│                          │  Testing &      │                                │
│                          │  Evaluation     │                                │
│                          └─────────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent 执行流程

### 总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      GenshinRetrievalAgent                       │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐             │
│  │  ReActAgent │  │ AnswerGrader│  │ QueryRefiner │             │
│  │  (LlamaIndex)│  │  (评分器)   │  │  (查询分解)  │             │
│  └─────────────┘  └─────────────┘  └──────────────┘             │
│         │                │                 │                     │
│         └────────────────┼─────────────────┘                     │
│                          │                                       │
│              ┌───────────┴───────────┐                          │
│              │     AgentTracer        │                          │
│              │   (完整日志追踪)        │                          │
│              └───────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌──────────┐      ┌──────────┐      ┌──────────┐
   │  Neo4j   │      │  Qdrant  │      │  Gemini  │
   │ 知识图谱  │      │  向量库   │      │   LLM    │
   └──────────┘      └──────────┘      └──────────┘
```

### 执行步骤 (chat_with_grading)

```
1. 初始化 → 2. 启动 Trace → 3. 重试循环 (max=3)
                                    │
        ┌───────────────────────────┘
        ▼
   ┌─────────────────────────────────────────────────────┐
   │ FOR attempt = 1 to 3:                               │
   │   a) 设置 limit (3→5→8 渐进扩展)                    │
   │   b) ReAct Agent 执行 (Thought→Action→Observation)  │
   │   c) Grader 评分 (4维度, 硬性门槛: depth≥10)        │
   │   d) 通过? → 跳出 / 失败? → Refiner 分解查询        │
   │   e) 构建历史上下文，注入下一轮                      │
   └─────────────────────────────────────────────────────┘
        │
        ▼
   4. 人文化处理 (去引用) → 5. 保存 Trace → 6. 返回答案
```

### 5 个检索工具

| 工具 | 用途 | 数据源 |
|------|------|--------|
| `lookup_knowledge` | 查询实体属性/直接关系 | Neo4j |
| `find_connection` | 查找两实体最短路径 | Neo4j |
| `track_journey` | 追踪关系时间线演变 | Neo4j |
| `get_character_events` | 获取角色重大事件 | Neo4j |
| `search_memory` | 语义搜索故事原文 | Qdrant |

### 评分机制

| 维度 | 权重 | 硬性门槛 |
|------|------|---------|
| Tool Usage | 25分 | - |
| Completeness | 25分 | - |
| Citation | 25分 | - |
| **Depth** | 25分 | **≥10 (必须)** |
| **Total** | 100分 | **≥70** |

### 关键设计特点

- **Progressive Limit Expansion**: limit 3→5→8 逐步扩大搜索范围
- **Structured Context Injection**: 失败时将历史结果注入下一轮
- **Hard Depth Threshold**: 强制要求答案包含具体证据/对话原文
- **Humanization**: 通过时移除学术化引用，保持自然表达
- **Full Tracing**: 完整日志记录每个 attempt 的工具调用、推理流、评分

详细设计文档: [design/system-architecture.md](./design/system-architecture.md)

---

## 文档状态说明

| 状态 | 含义 |
|------|------|
| `Draft` | 草稿，正在编写 |
| `In Review` | 评审中 |
| `Approved` | 已批准，可执行 |
| `Deprecated` | 已废弃，仅供参考 |
| `Superseded` | 已被新文档取代 |

---

## 版本历史

| 日期 | 变更 | 作者 |
|------|------|------|
| 2026-02-01 | 新增 Agent 执行流程文档 | - |
| 2026-01-29 | 按 Google Style 重构文档结构 | - |
| 2026-01-28 | ADR-006 v2.0 更新 (LlamaIndex FunctionAgent) | - |
| 2026-01-27 | 初始文档创建 | - |
