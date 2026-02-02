# Genshin Story QA System

> 基于 RAG + 知识图谱的原神剧情问答系统

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LlamaIndex](https://img.shields.io/badge/LlamaIndex-0.11+-green.svg)](https://docs.llamaindex.ai/)

## 项目概述

智能问答平台，让原神玩家通过自然语言快速查询和回顾游戏剧情内容，解决"剧情太长记不住"的痛点。

**核心特性**:
- **Graph-Vector 互补架构**: Neo4j 图数据库存储角色关系，Qdrant 向量数据库存储剧情文本
- **ReAct Agent**: 基于 LlamaIndex 的智能代理，自动选择合适的检索工具
- **多轮对话**: 支持代词消解和上下文追问
- **中文优化**: BGE 中文 Embedding + Jina Reranker

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Web UI (Streamlit)                      │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  RAG Engine │  │ ReAct Agent │  │   ChatMemoryBuffer  │ │
│  │ (LlamaIndex)│  │(FunctionAgent)│ │  (Multi-turn)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                      Storage Layer                          │
│  ┌─────────────┐  ┌─────────────┐                          │
│  │   Qdrant    │  │   Neo4j     │                          │
│  │ (Vectors)   │  │  (Graph)    │                          │
│  └─────────────┘  └─────────────┘                          │
├─────────────────────────────────────────────────────────────┤
│                      Model Layer                            │
│  ┌─────────────┐  ┌─────────────────────────────────────┐  │
│  │Gemini 2.5   │  │ BAAI/bge-base-zh-v1.5 (Embedding)   │  │
│  │  Flash      │  │ + Jina Reranker (Local)             │  │
│  └─────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 检索工具

系统提供 5 个正交的检索工具:

| 工具 | 数据源 | 用途 | 示例问题 |
|------|--------|------|----------|
| `lookup_knowledge` | Neo4j | 实体属性/关系查询 | "伊涅芙是谁？" |
| `find_connection` | Neo4j | 两实体间路径 | "恰斯卡和旅行者什么关系？" |
| `track_journey` | Neo4j | 时间线追踪 | "少女的经历是什么？" |
| `get_character_events` | Neo4j | 重大事件查询 | "少女是如何重回世界的？" |
| `search_memory` | Qdrant | 语义检索对话 | "玛薇卡说了什么？" |

## 知识图谱结构

### 节点类型
| Type | Count | Description |
|------|-------|-------------|
| Character | 276 | 角色实体 |
| Organization | 12 | 组织实体 |
| MajorEvent | TBD | 重大事件 |

### 关系类型
| Relation | Count | Description |
|----------|-------|-------------|
| PARTNER_OF | 207 | 搭档关系 |
| MEMBER_OF | 194 | 组织成员 |
| FRIEND_OF | 132 | 朋友关系 |
| INTERACTS_WITH | 107 | 互动关系 |
| ENEMY_OF | 87 | 敌对关系 |
| FAMILY_OF | 63 | 家庭关系 |
| LEADER_OF | 46 | 领导关系 |

## 快速开始

### 环境要求
- Python 3.11+
- Docker (Qdrant, Neo4j)
- Apple Silicon (MPS) 或 CUDA GPU (可选)

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd AmberProject

# 使用 uv 安装依赖
uv sync

# 启动数据库
docker-compose up -d
```

### 配置

创建 `.env` 文件:
```env
GEMINI_API_KEY=your_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=genshin_story_qa
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 运行

```bash
# 启动 Web UI
streamlit run src/ui/streamlit_app.py

# 或使用 CLI
python -m src.scripts.cli_agent
```

## 项目结构

```
AmberProject/
├── src/
│   ├── agent/           # ReAct Agent 实现
│   │   ├── agent.py     # 主 Agent 类
│   │   ├── grader.py    # 答案质量评估
│   │   ├── refiner.py   # 查询改写
│   │   └── prompts.py   # 系统提示词
│   ├── retrieval/       # 检索工具
│   │   ├── lookup_knowledge.py
│   │   ├── find_connection.py
│   │   ├── track_journey.py
│   │   ├── get_character_events.py
│   │   └── search_memory.py
│   ├── graph/           # Neo4j 图数据库
│   │   ├── searcher.py  # Cypher 查询封装
│   │   ├── builder.py   # 图构建
│   │   └── connection.py
│   ├── ingestion/       # 数据导入管道
│   │   ├── pipeline.py  # 主管道
│   │   ├── chunker.py   # 语义分块
│   │   ├── embedder.py  # BGE Embedding
│   │   ├── indexer.py   # Qdrant 索引
│   │   └── reranker.py  # Jina Reranker
│   ├── config/          # 配置
│   │   ├── settings.py
│   │   └── aliases.py   # 角色别名映射
│   └── ui/              # Streamlit UI
├── Data/                # 原始剧情数据
├── docs/                # 公开文档
├── docs_internal/       # 内部设计文档
├── tests/               # 测试
└── evaluation/          # 评测
```

## 文档

| 文档 | 位置 | 描述 |
|------|------|------|
| PRD | `docs/PRD.md` | 产品需求文档 |
| 系统架构 | `docs/design/system-architecture.md` | 技术栈与架构设计 |
| Agent 设计 | `docs/agent/architecture.md` | ReAct Agent 实现 |
| 数据管道 | `docs/dataInput/overview.md` | 数据导入流程 |
| 查询工具 | `docs/query/graph_query_tool.md` | 图查询 API |

## 开发指南

### 运行测试
```bash
pytest tests/
```

### 代码规范
- 使用 `ruff` 进行 linting
- 使用 `pyright` 进行类型检查
- 遵循 [Git Workflow](.claude/rules/git-workflow.md)

## License

MIT License
