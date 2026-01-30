# Agent 全链路追踪日志

## 概述

日志系统记录 ReAct Agent 每次查询的完整执行链路，用于调试和性能分析。

## 目录结构

```
logger/
└── traces/                    # JSON 追踪文件
    └── {timestamp}-{hash}.json
```

## 使用方法

### 查看最新追踪

```bash
# 完整输出
ls -t logger/traces/*.json | head -1 | xargs cat | jq .

# 摘要
cat logger/traces/*.json | jq '{query, passed, total_duration_ms, attempts: (.attempts | length)}'
```

### 分析工具调用

```bash
# 列出所有工具调用
cat logger/traces/*.json | jq '.attempts[].tool_calls[] | {tool, input}'

# 统计工具使用次数
cat logger/traces/*.json | jq '.attempts[].tool_calls[].tool' | sort | uniq -c
```

### 查看评分详情

```bash
cat logger/traces/*.json | jq '.attempts[].grading.output | {score, depth: .scores.depth, passed}'
```

### 查找失败的尝试

```bash
cat logger/traces/*.json | jq '.attempts[] | select(.grading.output.passed == false)'
```

### 查找特定查询

```bash
# 搜索关键词
grep -l "努昂诺塔" logger/traces/*.json

# 带上下文搜索
grep -r "努昂诺塔" logger/traces/ -A 2
```

### 性能分析

```bash
# 查看耗时分布
cat logger/traces/*.json | jq '{
  total: .total_duration_ms,
  grading: [.attempts[].grading.duration_ms] | add,
  tools: [.attempts[].tool_calls[].duration_ms] | add
}'
```

## 追踪内容

| 类别 | 记录内容 |
|------|----------|
| **tool_calls** | Neo4j/Qdrant 查询的输入参数和返回结果 |
| **reasoning** | ReAct 的 Thought -> Action -> Observation 链 |
| **grading** | Grader 的输入(问题、答案、工具调用)和输出(评分、建议) |
| **refiner** | 查询分解(当评分失败时触发) |
| **timing** | 各阶段执行时间(ms) |

## Trace JSON 结构

```json
{
  "trace_id": "20260130-174800-abc123",
  "timestamp": "2026-01-30T17:48:00Z",
  "query": "用户问题",
  "config": {
    "agent_model": "gemini-3-pro-preview",
    "grader_model": "gemini-2.5-flash",
    "max_retries": 2
  },
  "attempts": [{
    "attempt": 1,
    "limit": 5,
    "tool_calls": [
      {
        "tool": "find_connection",
        "input": {"entity1": "A", "entity2": "B"},
        "output": "A -[RELATION]-> B",
        "duration_ms": 50
      }
    ],
    "reasoning": {
      "raw_stream": "Thought: ...\nAction: ...\nObservation: ...",
      "thoughts": [],
      "actions": [],
      "observations": []
    },
    "grading": {
      "input": {
        "question": "...",
        "answer": "...",
        "tool_calls": [...]
      },
      "output": {
        "question_type": "关系类问题",
        "scores": {"tool_usage": 12, "evidence": 5, "completeness": 20, "citation": 20, "depth": 20},
        "score": 77,
        "passed": true,
        "reason": "...",
        "suggestion": "..."
      },
      "duration_ms": 2500
    },
    "refiner": {
      "input": {"question": "...", "suggestion": "..."},
      "output": {"queries": ["查询1", "查询2", "查询3"]},
      "duration_ms": 1500
    }
  }],
  "final_response": "最终答案...",
  "total_duration_ms": 40000,
  "passed": true
}
```

## 自动触发

追踪在 `chat_with_grading()` 调用时自动启用，文件保存到 `logger/traces/`。

```python
from src.agent import create_agent

agent = create_agent(enable_grader=True)
answer, history = await agent.chat_with_grading("问题")
# 追踪文件自动保存到 logger/traces/
```

## 追踪生命周期

1. **start_trace**: `chat_with_grading()` 开始时调用
2. **start_attempt**: 每次重试开始时调用
3. **log_tool_call**: 每次工具执行时调用
4. **log_reasoning_stream**: ReAct 推理输出时调用
5. **log_grading**: Grader 评估后调用
6. **log_refiner**: Refiner 分解查询后调用
7. **end_attempt**: 重试结束时调用
8. **end_trace**: 查询完成时调用，保存 JSON 文件

## 配置

默认日志目录为 `logger/traces/`。如需修改，可在 `AgentTracer` 初始化时指定：

```python
from src.agent.tracer import AgentTracer

tracer = AgentTracer(log_dir="custom/path/traces")
```
