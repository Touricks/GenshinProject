# Agent Architecture

> ReAct + Grader + Refiner 协同架构文档

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ReAct Agent Pipeline                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│    User Query                                                                        │
│        │                                                                             │
│        ▼                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                         ATTEMPT LOOP (max 3 rounds)                            │  │
│  │                                                                                │  │
│  │   ┌─────────────────────────────────────────────────────────────────────┐     │  │
│  │   │                     ReActAgent (LlamaIndex)                          │     │  │
│  │   │                                                                      │     │  │
│  │   │   Thought: 分析问题类型，选择合适工具                                  │     │  │
│  │   │      │                                                               │     │  │
│  │   │      ▼                                                               │     │  │
│  │   │   Action: 调用工具 (lookup_knowledge, search_memory, ...)            │     │  │
│  │   │      │                                                               │     │  │
│  │   │      ▼                                                               │     │  │
│  │   │   Observation: 工具返回结果                                           │     │  │
│  │   │      │                                                               │     │  │
│  │   │      ▼                                                               │     │  │
│  │   │   (循环直到 Agent 认为可以回答)                                        │     │  │
│  │   │      │                                                               │     │  │
│  │   │      ▼                                                               │     │  │
│  │   │   Answer: 生成答案                                                    │     │  │
│  │   └──────────────────────────────────┬──────────────────────────────────┘     │  │
│  │                                      │                                         │  │
│  │                                      ▼                                         │  │
│  │   ┌─────────────────────────────────────────────────────────────────────┐     │  │
│  │   │                     AnswerGrader (Hard Grader)                       │     │  │
│  │   │                                                                      │     │  │
│  │   │   评估 5 个维度 (每个 0-20 分):                                        │     │  │
│  │   │   - tool_usage: 工具调用验证                                          │     │  │
│  │   │   - evidence: 证据支持                                                │     │  │
│  │   │   - completeness: 答案完整性                                          │     │  │
│  │   │   - citation: 来源引用                                                │     │  │
│  │   │   - depth: 答案深度 (关系类问题需要具体事件)                            │     │  │
│  │   │                                                                      │     │  │
│  │   │   硬性门槛:                                                           │     │  │
│  │   │   - depth >= 8                                                       │     │  │
│  │   │   - evidence >= 5                                                    │     │  │
│  │   │   - total score >= 70                                                │     │  │
│  │   └──────────────────────────────────┬──────────────────────────────────┘     │  │
│  │                                      │                                         │  │
│  │                        ┌─────────────┴─────────────┐                          │  │
│  │                        │                           │                          │  │
│  │                     PASSED                      FAILED                        │  │
│  │                        │                           │                          │  │
│  │                        ▼                           ▼                          │  │
│  │                 Return Answer           ┌─────────────────────┐               │  │
│  │                                         │   QueryRefiner       │               │  │
│  │                                         │                      │               │  │
│  │                                         │  根据 Grader 建议     │               │  │
│  │                                         │  分解问题为多个       │               │  │
│  │                                         │  针对性搜索查询       │               │  │
│  │                                         │                      │               │  │
│  │                                         │  Output:             │               │  │
│  │                                         │  ["查询1", "查询2"]   │               │  │
│  │                                         └──────────┬──────────┘               │  │
│  │                                                    │                          │  │
│  │                                                    ▼                          │  │
│  │                                         Inject hints to next                  │  │
│  │                                         attempt's query                       │  │
│  │                                         + Increase search limit               │  │
│  │                                                    │                          │  │
│  └────────────────────────────────────────────────────┴──────────────────────────┘  │
│                                                                                      │
│                                                                                      │
│    ┌─────────────────────────────────────────────────────────────────────────────┐  │
│    │                           AgentTracer (Observability)                        │  │
│    │                                                                              │  │
│    │   Records full execution trace:                                             │  │
│    │   - Tool calls with input/output                                            │  │
│    │   - Reasoning stream (Thought/Action/Observation)                           │  │
│    │   - Grading results per attempt                                             │  │
│    │   - Refiner suggestions                                                     │  │
│    │   - Timing information                                                      │  │
│    │                                                                              │  │
│    │   Output: logger/traces/{timestamp}-{query_hash}.json                       │  │
│    └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 组件详解

### 1. ReActAgent (核心推理引擎)

**模块**: `src/agent/agent.py`

**职责**: 执行 Thought → Action → Observation 循环，调用工具获取信息并生成答案。

**关键特性**:
- 基于 LlamaIndex `ReActAgent` 实现
- 使用 Google Gemini LLM (默认 gemini-2.0-flash)
- 禁用 AFC (Automated Function Calling)，通过文本 prompt 控制工具调用
- 支持多轮对话 (通过 `Context` 维护状态)

**可用工具** (5个):

| 工具 | 数据源 | 用途 | 典型问题 |
|------|--------|------|----------|
| `lookup_knowledge` | Neo4j | 查询实体基本信息 | "X是谁？" |
| `find_connection` | Neo4j | 查找两实体关系路径 | "X和Y是什么关系？" |
| `track_journey` | Neo4j | 追踪关系变化历程 | "X是如何发展的？" |
| `get_character_events` | Neo4j | 获取重大事件 | "X是如何做到Y的？" |
| `search_memory` | Qdrant | 搜索故事原文 | "X说了什么？" |

**System Prompt 设计** (`src/agent/prompts.py`):
- 强制"先查后答"原则
- 工具选择决策树
- 关系类问题两步法: `find_connection` → `search_memory`
- 抽象问题策略: `get_character_events` 桥接抽象查询与具体事件

---

### 2. AnswerGrader (质量评估器)

**模块**: `src/agent/grader.py`

**职责**: 评估答案质量，决定是否需要重试。

**评分维度** (每个 0-20 分):

| 维度 | 说明 | 硬性门槛 |
|------|------|----------|
| `tool_usage` | 是否调用了适当的工具验证信息 | - |
| `evidence` | 答案是否基于工具返回的证据 | >= 5 |
| `completeness` | 是否完整回答了问题所有方面 | - |
| `citation` | 是否引用了来源 (Chapter/Task ID) | - |
| `depth` | 答案深度 (关系类需要具体事件描述) | >= 8 |

**通过条件**:
```
passed = depth >= 8 AND evidence >= 5 AND total_score >= 70
```

**问题类型识别**:
- 关系类: "X和Y是什么关系"、"X怎么认识Y"
- 事实类: "X是谁"、"X的称号是什么"
- 历程类: "X的经历"、"X是如何发展的"
- 细节类: "X说了什么"、"描述某个场景"

**关键设计**:
- 幻觉检测采用严格定义: 只有与 tool output 直接矛盾才算幻觉
- 允许对 tool output 的总结、归纳、合理推理
- 考虑 tool output 截断因素 (最多显示 2000 字符)

---

### 3. QueryRefiner (查询优化器)

**模块**: `src/agent/refiner.py`

**职责**: 当 Grader 判定答案不足时，分解问题为多个针对性搜索查询。

**触发条件**: Grader 返回 `passed=False`

**输入**:
- 原始用户问题
- Grader 的改进建议 (`suggestion` 字段)

**输出**: 2-3 个针对性搜索查询 (JSON 数组)

**示例**:
```
问题: "努昂诺塔和少女是什么关系？"
建议: "答案深度不足，请调用 search_memory 获取具体剧情内容"

输出: ["努昂诺塔 少女 相遇 见面", "努昂诺塔 创造 诞生 灵魂", "少女 月灵 起源"]
```

**Hint 注入格式**:
```
{原始问题}

[系统提示: 上次答案深度不足。建议搜索关键词: "查询1", "查询2", "查询3"。
可以使用 search_memory 搜索故事内容，track_journey 追踪时间线，
或 find_connection 查找关系。请根据问题类型选择合适的工具。]
```

---

### 4. AgentTracer (可观测性)

**模块**: `src/agent/tracer.py`

**职责**: 记录完整执行链路，用于调试和性能分析。

**记录内容**:
- 每次工具调用的输入/输出
- ReAct 推理流 (Thought/Action/Observation)
- 每轮 Grading 结果
- Refiner 生成的查询建议
- 时间戳和耗时

**输出格式**: JSON 文件

**存储位置**: `logger/traces/{timestamp}-{query_hash}.json`

**Trace 结构**:
```json
{
  "trace_id": "20260130-211013-7bdcf4",
  "query": "少女是如何重回世界的",
  "config": {
    "agent_model": "gemini-2.0-flash",
    "grader_model": "gemini-2.5-flash",
    "max_retries": 3
  },
  "attempts": [
    {
      "attempt": 1,
      "limit": 3,
      "tool_calls": [...],
      "reasoning": {
        "raw_stream": "Thought: ... Action: ... Observation: ...",
        "thoughts": [...],
        "actions": [...],
        "observations": [...]
      },
      "grading": {
        "input": {...},
        "output": {
          "score": 65,
          "scores": {"depth": 5, "evidence": 15, ...},
          "passed": false,
          "suggestion": "答案深度不足..."
        }
      },
      "refiner": {
        "queries": ["少女 献出 身体", "少女 月光 转变"]
      }
    }
  ],
  "final_response": "...",
  "passed": true,
  "total_duration_ms": 42000
}
```

---

## 渐进式重试机制

### Limit Progression (搜索限制递增)

| 轮次 | search_memory limit | 策略 |
|------|---------------------|------|
| 1 | 3 | 少量精确结果 |
| 2 | 3 | 继续少量 + 新查询词 |
| 3 | 5 | 略微扩大范围 |

**设计理念**: 广度优先 - 每次少量精确结果 + 多工具组合，而非一次性返回大量结果。

### 重试流程

```
┌─────────────────────────────────────────────────────────────────┐
│  Attempt 1 (limit=3)                                            │
│  → Agent 生成答案                                                │
│  → Grader: depth=5, score=60, FAILED (depth < 8)                │
│  → Refiner: ["少女 献出 身体", "三月 权能 转交"]                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Attempt 2 (limit=3)                                            │
│  Query: 原始问题 + [系统提示: 建议搜索关键词...]                   │
│  → Agent 使用 Refiner 建议的关键词                               │
│  → Grader: depth=12, score=78, PASSED                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        Return Answer
```

---

## 模型配置

| 组件 | 模型 | 用途 |
|------|------|------|
| ReActAgent | `gemini-2.0-flash` (可配置) | 主推理引擎 |
| AnswerGrader | `gemini-2.5-flash` (GRADER_MODEL) | 快速评分 |
| QueryRefiner | 与 ReActAgent 同模型 | 需要强推理能力 |

**配置方式**:
```python
# settings.py
LLM_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GRADER_MODEL = os.getenv("GRADER_MODEL", "gemini-2.5-flash")
```

---

## 数据流示例

### 问题: "少女是如何重回世界的？"

```
1. [ReAct] Thought: 这是历程类问题，需要先获取少女的重大事件
2. [ReAct] Action: get_character_events(entity="少女")
3. [ReAct] Observation: [events: 献出身体, 三月权能转交, 化作月光...]
4. [ReAct] Thought: 需要更多细节
5. [ReAct] Action: search_memory(query="少女 献出 身体")
6. [ReAct] Observation: [故事原文片段...]
7. [ReAct] Answer: 根据第16章任务1608，少女通过献出身体...

8. [Grader] 评估:
   - tool_usage: 18 (调用了适当工具)
   - evidence: 16 (有证据支持)
   - completeness: 14 (回答了主要方面)
   - citation: 15 (引用了章节)
   - depth: 15 (描述了具体事件)
   - total: 78 → PASSED

9. [Tracer] 保存完整执行链到 logger/traces/
```

---

## 文件结构

```
src/agent/
├── __init__.py          # 模块导出
├── agent.py             # GenshinRetrievalAgent 主类
├── grader.py            # AnswerGrader 评分器
├── refiner.py           # QueryRefiner 查询优化器
├── tracer.py            # AgentTracer 链路追踪
└── prompts.py           # SYSTEM_PROMPT 系统提示词
```

---

## 相关文档

| 文档 | 内容 |
|------|------|
| [agent.md](./agent.md) | Agent 调用方法详解 |
| [../query/](../query/) | 检索工具 API 文档 |
| [../dataInput/event-extraction-pipeline.md](../dataInput/event-extraction-pipeline.md) | MajorEvent 提取 (get_character_events 数据来源) |
