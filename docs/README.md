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
| 2026-01-29 | 按 Google Style 重构文档结构 | - |
| 2026-01-28 | ADR-006 v2.0 更新 (LlamaIndex FunctionAgent) | - |
| 2026-01-27 | 初始文档创建 | - |
