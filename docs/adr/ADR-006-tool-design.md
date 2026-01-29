# ADR-006: 最终检索工具集设计

> **状态**: Approved
> **创建时间**: 2026-01-28T23:00:00+08:00
> **修订时间**: 2026-01-28T23:30:00+08:00
> **前置文档**: ADR-001 ~ ADR-005
> **决策**:
> - 确定 4 个核心检索工具
> - 使用 Gemini 原生 Function Calling 实现
> - 代词消解由 Agent 处理，无需 SFT

---

## 1. 决策摘要

### 1.1 最终工具集

| ID | 名称 | 功能 | 确定性 |
|----|------|------|--------|
| T1 | `vector_search` | 通用向量检索 (支持过滤) | ✅ |
| T2 | `graph_search` | 图结构检索 (关系查询) | ✅ |
| T3 | `track_entity` | 实体时序追踪 (事件演变) | ✅ |
| T4 | `stop` | 终止检索 | ✅ |

### 1.2 关键决策

| 决策 | 结论 | 理由 |
|------|------|------|
| `entity_lookup` | **去除** | 可被 `vector_search` 覆盖 |
| `session_search` | **不需要** | 代词消解在 Thought 中完成 |
| `sort_temporal` | **内置** | 作为 `track_entity` 内部实现 |
| 代词消解 | **Agent Thought** | 利用 Gemini 能力，非独立工具 |

---

## 2. 工具详细定义

### T1: vector_search

```python
def vector_search(
    query: str,
    top_k: int = 10,
    chapter_filter: tuple = None,    # (start, end) 章节范围
    entity_filter: str = None        # 实体过滤
) -> List[Chunk]:
    """
    通用向量检索，支持可选过滤条件

    适用场景:
    - 简单事实查询: "玛拉妮的性格是什么？"
    - 带过滤的查询: "第3章中基尼奇做了什么？"
    - 实体相关查询: "阿尤的能力是什么？"

    实现:
    1. query → embedding
    2. Qdrant 向量检索 (top_k * 3)
    3. 应用 chapter_filter (如有)
    4. 应用 entity_filter (如有)
    5. 按相似度排序，返回 top_k
    """
    results = qdrant.search(embed(query), top_k=top_k * 3)

    if chapter_filter:
        start, end = chapter_filter
        results = [r for r in results if start <= r.metadata.chapter <= end]

    if entity_filter:
        results = [r for r in results if entity_filter in r.metadata.entities]

    return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
```

### T2: graph_search

```python
def graph_search(
    entity: str,
    relation: str = None,    # 可选: "friend_of", "enemy_of", "member_of" 等
    depth: int = 2           # 遍历深度
) -> List[Chunk]:
    """
    从实体出发的图遍历检索

    适用场景:
    - 关系查询: "恰斯卡和卡齐娜是什么关系？"
    - 社交网络: "基尼奇的朋友有哪些？"
    - 组织关系: "流泉之众的成员有谁？"

    实现:
    1. 在 Neo4j 中找到 entity 节点
    2. 按 relation 类型遍历 (depth 层)
    3. 收集相关节点
    4. 获取节点对应的文本 chunks
    """
    neighbors = neo4j.traverse(
        start_node=entity,
        max_depth=depth,
        relation_type=relation  # None 表示所有关系类型
    )

    related_chunks = fetch_chunks_for_entities(neighbors)
    return related_chunks
```

### T3: track_entity

```python
def track_entity(
    entity: str,
    chapter_range: tuple = (1, 999)  # 默认全范围
) -> List[Chunk]:
    """
    追踪实体在时间线上的出现，按时序排列

    适用场景:
    - 事件演变: "旅行者如何获得古名？"
    - 角色成长: "基尼奇的冒险经历是怎样的？"
    - 关系变化: "A和B的关系如何演变？"

    实现:
    1. 按 entity 过滤所有 chunks
    2. 按 chapter_range 过滤
    3. 按 (chapter, event_order) 时序排序
    """
    chunks = qdrant.search_by_metadata(
        entity_filter=entity,
        chapter_range=chapter_range
    )

    # 内置时序排序 (原 sort_temporal)
    sorted_chunks = sorted(
        chunks,
        key=lambda x: (x.metadata.chapter, x.metadata.event_order)
    )

    return sorted_chunks
```

### T4: stop

```python
def stop() -> None:
    """
    终止检索，进入答案生成阶段

    触发条件 (Agent 在 Thought 中判断):
    - 信息已充分，可以回答问题
    - 达到最大检索轮次 (5 轮)
    - 确认无法找到相关信息
    """
    pass
```

---

## 3. 去除的工具及理由

### 3.1 entity_lookup (去除)

```python
# 原设计
def entity_lookup(entity_name: str) -> EntityInfo:
    """快速查询实体基本信息"""
    ...

# 为何去除: 可被 vector_search 覆盖
vector_search(query="阿尤", entity_filter="阿尤", top_k=3)
# → 返回包含阿尤的 chunks，信息充分
```

### 3.2 session_search (不添加)

```python
# 原设计
def session_search(query: str, session_entities: List[str]) -> List[Chunk]:
    """会话上下文增强检索"""
    ...

# 为何不添加: 代词消解应在 Agent Thought 中完成
# Agent 改写 query 后，使用 vector_search 即可
```

### 3.3 sort_temporal (内置)

```python
# 原设计: 独立工具
def sort_temporal(chunks: List[Chunk]) -> List[Chunk]:
    """对已有 chunks 按时间排序"""
    ...

# 为何内置: 不是检索工具，是后处理
# 已内置于 track_entity 中
```

---

## 4. 代词消解处理方案

### 4.1 设计决策

**代词消解由 Gemini Agent 在 Thought 中完成，不需要独立工具**

### 4.2 实现架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    多轮对话处理流程                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │         Session Context Manager (系统组件，非工具)          │   │
│  │                                                             │   │
│  │  维护内容:                                                  │   │
│  │  - entity_stack: 最近提到的实体 [基尼奇, 阿尤]             │   │
│  │  - recent_topic: 最近话题 "龙伙伴"                         │   │
│  │  - turn_history: 对话历史摘要                              │   │
│  │                                                             │   │
│  │  职责: 将上下文注入 Gemini Prompt，不参与检索              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Gemini Agent (ReAct)                           │   │
│  │                                                             │   │
│  │  Input:                                                     │   │
│  │  - User Query: "它在任务中做了什么？"                       │   │
│  │  - Session Context: {entities: [基尼奇, 阿尤], topic: ...}  │   │
│  │                                                             │   │
│  │  [Thought]                                                  │   │
│  │  1. "它"是代词，指代上文的"阿尤"（基尼奇的龙伙伴）         │   │
│  │  2. 改写问题: "阿尤在任务中做了什么？"                      │   │
│  │  3. 这是关于特定实体行为的查询                              │   │
│  │                                                             │   │
│  │  [Action] vector_search(query="阿尤 任务 行动",             │   │
│  │                         entity_filter="阿尤")               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│                    确定性工具执行 (T1-T4)                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Prompt 中的 Session Context 注入

```markdown
# Session Context
最近提到的实体: 基尼奇, 阿尤(基尼奇的龙伙伴)
最近话题: 龙伙伴的名字
对话历史:
- User: "基尼奇的龙伙伴叫什么？"
- Assistant: "基尼奇的龙伙伴叫阿尤。"

# Current Query
User: "它在任务中做了什么？"

# Instructions
1. 如果 query 中有代词 (他/她/它/他们等)，先根据 Session Context 消解
2. 改写 query 后选择合适的工具
```

---

## 5. 工具选择指南

### 5.1 问题类型 → 工具映射

| 问题类型 | 示例 | 推荐工具 | 参数 |
|----------|------|----------|------|
| **简单事实** | "X是什么？" | T1 | query |
| **带范围事实** | "第3章X做了什么？" | T1 | query, chapter_filter |
| **实体属性** | "X的Y是什么？" | T1 | query, entity_filter |
| **关系查询** | "X和Y什么关系？" | T2 | entity, relation |
| **社交网络** | "X的朋友有谁？" | T2 | entity, depth=2 |
| **事件演变** | "X如何发展？" | T3 | entity, chapter_range |
| **角色成长** | "X的经历？" | T3 | entity |
| **多轮指代** | "它做了什么？" | Thought消解 → T1/T2/T3 | - |

### 5.2 组合使用示例

```
Q: "恰斯卡和卡齐娜的关系如何演变？"

[Thought] 这是关系+演变的复合问题，需要:
1. 先用 graph_search 找到关系类型
2. 再用 track_entity 追踪关系变化

[Action] graph_search(entity="恰斯卡", relation=None, depth=2)
[Observation] 找到: 恰斯卡 --friend_of--> 卡齐娜

[Thought] 确认是朋友关系，现在追踪时间演变
[Action] track_entity(entity="恰斯卡", chapter_range=(1, 10))
[Observation] 按时序找到她们互动的所有场景...

[Thought] 信息充分
[Action] stop()
```

---

## 6. LlamaIndex FunctionAgent 实现

### 6.1 为什么使用 LlamaIndex Agent

| 方案 | 格式保证 | 代码量 | 框架统一 | 切换 LLM |
|------|----------|--------|----------|----------|
| Gemini Native FC + 自建 Loop | ✅ API 强制 | ~100 行 | ❌ 分离 | ❌ 重构 |
| **LlamaIndex FunctionAgent** | ✅ 框架保证 | ~10 行 | ✅ 统一 | ✅ 简单 |

**结论**: 使用 LlamaIndex `FunctionAgent`，统一 Indexing 和 Agent 框架，减少代码量，易于切换 LLM Provider。

### 6.2 工具定义 (LlamaIndex FunctionTool)

```python
from llama_index.core.tools import FunctionTool
from typing import List, Dict, Optional

# T1: vector_search
def vector_search(
    query: str,
    top_k: int = 10,
    chapter_filter: Optional[List[int]] = None,
    entity_filter: Optional[str] = None
) -> List[Dict]:
    """
    通用向量检索。用于简单事实查询、实体属性查询。支持章节范围和实体过滤。

    Args:
        query: 检索的关键词或问题
        top_k: 返回结果数量，默认10
        chapter_filter: 章节范围 [起始章节, 结束章节]，可选
        entity_filter: 过滤包含特定实体的结果，可选
    """
    # 实现见 Section 6.4
    ...

# T2: graph_search
def graph_search(
    entity: str,
    relation: Optional[str] = None,
    depth: int = 2
) -> List[Dict]:
    """
    图结构检索。用于关系查询（如'A和B什么关系'）、社交网络查询（如'A的朋友有谁'）。

    Args:
        entity: 起始实体名称
        relation: 关系类型(friend_of/enemy_of/member_of等)，不指定则查询所有关系
        depth: 图遍历深度，默认2
    """
    ...

# T3: track_entity
def track_entity(
    entity: str,
    chapter_range: Optional[List[int]] = None
) -> List[Dict]:
    """
    实体时序追踪。用于事件演变查询（如'X如何发展'）、角色成长查询。返回按时间排序的结果。

    Args:
        entity: 要追踪的实体名称
        chapter_range: 章节范围 [起始, 结束]，默认全范围
    """
    ...

# T4: stop
def stop(reason: str) -> None:
    """
    停止检索。当已收集到足够信息可以回答问题时调用。

    Args:
        reason: 停止原因 - sufficient(信息充分)/max_turns(达到上限)/not_found(无法找到)
    """
    pass

# 创建 FunctionTool 列表 (LlamaIndex 自动从 docstring 提取参数描述)
tools = [
    FunctionTool.from_defaults(fn=vector_search),
    FunctionTool.from_defaults(fn=graph_search),
    FunctionTool.from_defaults(fn=track_entity),
    FunctionTool.from_defaults(fn=stop),
]
```

### 6.3 Agent 实现 (LlamaIndex FunctionAgent)

```python
from llama_index.core.agent import FunctionAgent
from llama_index.llms.gemini import Gemini
from llama_index.core.memory import ChatMemoryBuffer
import os

# System Prompt
SYSTEM_PROMPT = """你是原神剧情检索专家 Agent。

任务：通过调用检索工具，收集回答用户问题所需的信息。

可用工具：
- vector_search: 通用向量检索，适合简单事实查询
- graph_search: 图结构检索，适合关系查询
- track_entity: 实体时序追踪，适合事件演变查询
- stop: 信息充分时停止检索

规则：
1. 分析问题，选择最合适的工具
2. 如果问题中有代词(他/她/它)，先根据对话历史消解后再检索
3. 每次只调用一个工具
4. 根据返回结果决定是否需要继续检索
5. 最多进行 5 轮检索
6. 信息充分时调用 stop"""


class GenshinRetrievalAgent:
    """基于 LlamaIndex FunctionAgent 的原神剧情检索 Agent"""

    def __init__(self):
        # LLM - Gemini 2.5 系列支持 Function Calling
        self.llm = Gemini(
            model="models/gemini-2.5-flash",
            api_key=os.getenv("GOOGLE_API_KEY")
        )

        # Memory (替代原 Session Context Manager)
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=4096)

        # Agent (LlamaIndex 内置 loop，无需自建)
        self.agent = FunctionAgent(
            tools=tools,  # 见 Section 6.2
            llm=self.llm,
            system_prompt=SYSTEM_PROMPT,
            max_function_calls=5,  # 原 max_turns=5
            verbose=True,  # 显示内部决策过程
        )

    async def run(self, query: str) -> str:
        """
        执行检索并返回答案

        Args:
            query: 用户问题

        Returns:
            生成的答案
        """
        response = await self.agent.run(query)
        return str(response)

    async def chat(self, query: str) -> str:
        """
        多轮对话模式 (使用 Memory)

        Args:
            query: 用户问题

        Returns:
            生成的答案
        """
        # Memory 自动管理对话历史，支持代词消解
        response = await self.agent.run(query)
        return str(response)
```

**关键简化**:
- 无需 `_build_prompt()`: System Prompt 由 FunctionAgent 管理
- 无需 `_execute_tool()`: FunctionAgent 自动执行工具
- 无需 `_format_result()`: FunctionAgent 自动处理返回值
- 无需 while loop: FunctionAgent 内置循环逻辑
- Memory 由 `ChatMemoryBuffer` 管理，自动支持代词消解

### 6.4 工具执行函数（确定性）

```python
from typing import List, Dict, Tuple, Optional
from qdrant_client import QdrantClient
from neo4j import GraphDatabase

# 初始化客户端
qdrant = QdrantClient(host="localhost", port=6333)
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687")

def vector_search(
    query: str,
    top_k: int = 10,
    chapter_filter: Optional[List[int]] = None,
    entity_filter: Optional[str] = None
) -> List[Dict]:
    """T1: 向量检索（确定性）"""

    # 1. Query embedding
    query_vector = embed(query)

    # 2. 构建过滤条件
    filters = {}
    if chapter_filter and len(chapter_filter) == 2:
        filters["chapter"] = {"$gte": chapter_filter[0], "$lte": chapter_filter[1]}
    if entity_filter:
        filters["entities"] = {"$contains": entity_filter}

    # 3. Qdrant 检索
    results = qdrant.search(
        collection_name="genshin_story",
        query_vector=query_vector,
        limit=top_k,
        query_filter=filters if filters else None
    )

    # 4. 格式化返回
    return [
        {
            "text": r.payload.get("text", ""),
            "chapter": r.payload.get("chapter"),
            "entities": r.payload.get("entities", []),
            "score": r.score
        }
        for r in results
    ]


def graph_search(
    entity: str,
    relation: Optional[str] = None,
    depth: int = 2
) -> List[Dict]:
    """T2: 图检索（确定性）"""

    with neo4j_driver.session() as session:
        # 构建 Cypher 查询
        if relation:
            query = f"""
            MATCH (a {{name: $entity}})-[r:{relation}*1..{depth}]-(b)
            RETURN DISTINCT b.name as name, type(r) as relation, b.description as description
            LIMIT 20
            """
        else:
            query = f"""
            MATCH (a {{name: $entity}})-[r*1..{depth}]-(b)
            RETURN DISTINCT b.name as name, type(r) as relation, b.description as description
            LIMIT 20
            """

        result = session.run(query, entity=entity)
        neighbors = [dict(record) for record in result]

    # 获取相关 chunks
    chunks = []
    for neighbor in neighbors:
        neighbor_chunks = vector_search(
            query=neighbor["name"],
            top_k=2,
            entity_filter=neighbor["name"]
        )
        chunks.extend(neighbor_chunks)

    return chunks


def track_entity(
    entity: str,
    chapter_range: Optional[List[int]] = None
) -> List[Dict]:
    """T3: 实体时序追踪（确定性）"""

    # 默认章节范围
    if not chapter_range:
        chapter_range = [1, 999]

    # 按实体和章节检索
    results = vector_search(
        query=entity,
        top_k=30,
        chapter_filter=chapter_range,
        entity_filter=entity
    )

    # 按时序排序
    sorted_results = sorted(
        results,
        key=lambda x: (x.get("chapter", 0), x.get("event_order", 0))
    )

    return sorted_results
```

### 6.5 使用示例

```python
import asyncio

# 创建 Agent
agent = GenshinRetrievalAgent()

# 示例 1: 简单查询
async def example_simple():
    result = await agent.run("玛拉妮的性格是什么？")
    print(result)
    # [Tool Call] vector_search(query='玛拉妮 性格')
    # [Tool Call] stop(reason='sufficient')
    # 答案: 玛拉妮性格热情直率...

# 示例 2: 关系查询
async def example_relation():
    result = await agent.run("恰斯卡和卡齐娜是什么关系？")
    print(result)
    # [Tool Call] graph_search(entity='恰斯卡')
    # [Tool Call] stop(reason='sufficient')
    # 答案: 恰斯卡和卡齐娜是朋友/战友关系...

# 示例 3: 多轮对话（代词消解 - Memory 自动处理）
async def example_multi_turn():
    await agent.chat("基尼奇的龙伙伴叫什么？")
    # 答案: 阿尤
    result = await agent.chat("它在任务中做了什么？")
    # Memory 自动消解 "它" → "阿尤"
    # [Tool Call] vector_search(query='阿尤 任务', entity_filter='阿尤')
    print(result)
    # 答案: 阿尤（基尼奇的龙伙伴）在任务中协助基尼奇...

# 示例 4: 时序追踪
async def example_temporal():
    result = await agent.run("旅行者如何获得古名？")
    print(result)
    # [Tool Call] track_entity(entity='旅行者')
    # [Tool Call] vector_search(query='古名 获得')
    # [Tool Call] stop(reason='sufficient')
    # 答案: 旅行者通过参加竞技场试炼获得古名...

# 运行
asyncio.run(example_simple())
```

### 6.6 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 框架 | **LlamaIndex FunctionAgent** | 统一框架，减少代码量 |
| 工具调用方式 | **FunctionTool.from_defaults()** | 自动从 docstring 提取参数描述 |
| Memory 管理 | **ChatMemoryBuffer** | 内置多轮对话支持，自动代词消解 |
| LLM Provider | **Gemini 2.5 (via llama-index-llms-gemini)** | 支持 FC，易切换 fallback |
| 是否需要 SFT | **不需要** | LlamaIndex + Gemini 指令遵循能力足够 |

---

## 7. 与其他 ADR 的关系

| ADR | 状态 | 与本 ADR 关系 |
|-----|------|---------------|
| ADR-001 | 被取代 | 不再需要 DPO，使用 Function Calling |
| ADR-002 | 参考 | DPO vs DAPO 分析仍有参考价值 |
| ADR-003 | 被取代 | ReAct 实现方式改为 Function Calling |
| ADR-004 | 参考 | GRPO vs DPO 分析仍有参考价值 |
| ADR-005 | **关联** | 本 ADR 是 ADR-005 的具体实现方案 |

---

## 8. 实现检查清单

### 8.1 LlamaIndex Agent 配置

- [ ] 安装依赖: `llama-index-core`, `llama-index-llms-gemini`
- [ ] GOOGLE_API_KEY 环境变量配置
- [ ] FunctionTool 定义 (4 个工具)
- [ ] System Prompt 编写
- [ ] FunctionAgent 初始化

### 8.2 工具函数实现

- [ ] T1 `vector_search`: Qdrant 检索 + 过滤逻辑
- [ ] T2 `graph_search`: Neo4j 遍历 + Chunk 获取
- [ ] T3 `track_entity`: 元数据检索 + 时序排序
- [ ] T4 `stop`: 终止信号处理

### 8.3 支撑组件

- [ ] ChatMemoryBuffer: 多轮对话记忆
- [ ] Chunk Metadata Schema: chapter, event_order, entities
- [ ] Embedding 函数: query → vector (BGE-base-zh-v1.5)

### 8.4 测试用例

- [ ] 单工具测试: 每个 FunctionTool 的基本功能
- [ ] Agent 端到端测试: 简单查询 → 答案
- [ ] 多轮检索测试: 复杂问题的多工具协作
- [ ] 代词消解测试: 多轮对话场景 (ChatMemoryBuffer)

---

## 9. 结论

### 9.1 最终架构

```
┌─────────────────────────────────────────────────────────────────────┐
│              系统架构 (LlamaIndex FunctionAgent)                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  User Query                                                         │
│      │                                                              │
│      ▼                                                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │           LlamaIndex FunctionAgent                           │  │
│  │                                                              │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │  System Prompt + FunctionTools                         │ │  │
│  │  │  - 角色定义: 原神剧情检索专家                          │ │  │
│  │  │  - 工具列表: vector_search, graph_search,              │ │  │
│  │  │              track_entity, stop                        │ │  │
│  │  │  - 规则: 代词消解, 最多5轮, 信息充分时stop             │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  │                         │                                    │  │
│  │                         ▼                                    │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │  ChatMemoryBuffer (多轮对话记忆)                       │ │  │
│  │  │  - 自动管理对话历史                                    │ │  │
│  │  │  - 支持代词消解                                        │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  │                         │                                    │  │
│  │                         ▼                                    │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │  Gemini LLM (via llama-index-llms-gemini)              │ │  │
│  │  │  - Gemini 2.5 Flash/Pro                                │ │  │
│  │  │  - 原生 Function Calling 支持                          │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                         │                                           │
│          Tool Calls     │  Tool Results (自动处理)                  │
│                         ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              FunctionTool 执行层 (确定性，本地)               │  │
│  │                                                              │  │
│  │   FunctionTool ────────┬── vector_search ──▶ Qdrant          │  │
│  │                        ├── graph_search ───▶ Neo4j           │  │
│  │                        ├── track_entity ───▶ Qdrant + Sort   │  │
│  │                        └── stop ───────────▶ 终止循环        │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                         │                                           │
│                         ▼                                           │
│                      Answer                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

关键点:
- 统一框架: Indexing 和 Agent 都用 LlamaIndex
- 内置 Loop: 无需自建 Agent 循环，减少 ~100 行代码
- Memory 管理: ChatMemoryBuffer 自动处理多轮对话和代词消解
- Provider 切换: 易于切换 Gemini ↔ Claude fallback
```

### 9.2 核心原则

1. **工具必须确定性**: 所有工具无内部 LLM 调用
2. **智能在 Agent**: 推理、决策、代词消解由 Gemini 处理
3. **工具集最小化**: 4 个工具足够覆盖所有场景
4. **可组合**: 复杂问题通过多轮工具调用解决
5. **无需 SFT**: 使用原生 Function Calling，格式由 API 保证

### 9.3 技术栈确认

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| Agent 框架 | LlamaIndex FunctionAgent | 统一框架，内置 loop |
| LLM | Gemini 2.5 Flash/Pro | via llama-index-llms-gemini |
| Memory | ChatMemoryBuffer | 多轮对话记忆 |
| 向量库 | Qdrant | 向量存储 |
| 图数据库 | Neo4j | 关系存储 |
| Embedding | BGE-base-zh-v1.5 | 本地部署 |

---

## 附录 A: 文件更新记录

| 时间 | 版本 | 变更 |
|------|------|------|
| 2026-01-28T23:00:00 | v1.0 | 初始版本，确定 4 工具架构 |
| 2026-01-28T23:30:00 | v2.0 | 新增 Gemini Function Calling 实现方案 |

## 附录 B: 相关代码文件

```
src/
├── agent/
│   ├── __init__.py
│   ├── agent.py              # GenshinRetrievalAgent (LlamaIndex FunctionAgent)
│   ├── tools.py              # FunctionTool.from_defaults() 定义
│   └── memory.py             # ChatMemoryBuffer 配置
├── retrieval/
│   ├── __init__.py
│   ├── vector_search.py      # T1 实现
│   ├── graph_search.py       # T2 实现
│   └── track_entity.py       # T3 实现
└── config/
    └── prompts.py            # System Prompt 模板
```
