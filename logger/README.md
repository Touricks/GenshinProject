# Agent Trace Logs

This directory contains full execution traces for debugging the ReAct agent.

## Directory Structure

```
logger/
├── traces/                    # JSON trace files
│   └── {timestamp}-{hash}.json
└── README.md                  # This file
```

## Trace Format

Each JSON file in `traces/` contains the complete execution trace:

| Field | Description |
|-------|-------------|
| `trace_id` | Unique identifier: `{YYYYMMDD-HHMMSS}-{query_hash}` |
| `timestamp` | ISO 8601 start timestamp |
| `query` | Original user question |
| `config` | Agent/model configuration |
| `attempts` | List of execution attempts |
| `final_response` | Final answer returned to user |
| `total_duration_ms` | Total execution time in milliseconds |
| `passed` | Whether grading passed |

## Attempt Structure

Each attempt in the `attempts` array contains:

```json
{
  "attempt": 1,
  "limit": 5,
  "tool_calls": [
    {
      "tool": "find_connection",
      "input": {"entity1": "努昂诺塔", "entity2": "少女"},
      "output": "努昂诺塔 -[INTERACTS_WITH]-> 少女",
      "duration_ms": 50
    }
  ],
  "reasoning": {
    "raw_stream": "Thought: 关系类问题...\nAction: find_connection...",
    "thoughts": ["关系类问题，需要两步查询"],
    "actions": ["find_connection", "search_memory"],
    "observations": ["INTERACTS_WITH", "[故事片段...]"]
  },
  "response": "努昂诺塔与「少女」之间存在着...",
  "grading": {
    "input": {
      "question": "努昂诺塔和少女是什么关系",
      "answer": "[truncated]...",
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
}
```

## Usage Examples

### View Latest Trace

```bash
# Pretty print with jq
ls -t logger/traces/*.json | head -1 | xargs cat | jq .

# Quick summary
ls -t logger/traces/*.json | head -1 | xargs cat | jq '{query, passed, total_duration_ms, attempts: (.attempts | length)}'
```

### Find Traces by Query

```bash
# Search for specific keywords
grep -l "努昂诺塔" logger/traces/*.json

# Search with context
grep -r "努昂诺塔" logger/traces/ -A 2
```

### Analyze Tool Calls

```bash
# List all tool calls from latest trace
cat logger/traces/*.json | jq '.attempts[].tool_calls[] | {tool, input}'

# Count tool calls by type
cat logger/traces/*.json | jq '.attempts[].tool_calls[].tool' | sort | uniq -c
```

### Check Grading Results

```bash
# View grading scores
cat logger/traces/*.json | jq '.attempts[].grading.output | {score, depth: .scores.depth, passed}'

# Find failed attempts
cat logger/traces/*.json | jq '.attempts[] | select(.grading.output.passed == false) | {attempt, score: .grading.output.score}'
```

### Performance Analysis

```bash
# View timing breakdown
cat logger/traces/*.json | jq '{
  total: .total_duration_ms,
  grading: [.attempts[].grading.duration_ms] | add,
  tools: [.attempts[].tool_calls[].duration_ms] | add
}'
```

## Trace Lifecycle

1. **start_trace**: Called when `chat_with_grading()` begins
2. **start_attempt**: Called for each retry attempt
3. **log_tool_call**: Called for each tool execution
4. **log_reasoning_stream**: Called for ReAct reasoning output
5. **log_grading**: Called after grader evaluation
6. **log_refiner**: Called if refiner is used
7. **end_attempt**: Called when attempt completes
8. **end_trace**: Called when query completes, saves JSON file

## Configuration

The tracer is automatically enabled when using `chat_with_grading()`.
Traces are saved to `logger/traces/` by default.

To change the log directory, modify the `AgentTracer` initialization in `src/agent/agent.py`.
