# Agent 调用方法

> 本文档说明如何调用 ReAct Agent 的各种方法。

## 概览

| 方法 | 模式 | 上下文 | 日志 | 评分 | 适用场景 |
|------|------|--------|------|------|----------|
| `chat_with_grading` | 多轮 | 保留 | 工具调用+评分 | Hard Grader | 质量保证，迭代深化 |
| `chat_verbose` | 多轮 | 保留 | Thought/Action/Observation | 无 | 调试，理解推理过程 |
| `chat` | 多轮 | 保留 | 最小化 | 无 | 常规对话 |
| `run` | 单次 | 无 | 最小化 | 无 | 一次性查询 |

---

## 方法详解

### 1. `chat_with_grading(query, max_retries=3) -> Tuple[str, List[dict]]`

带 Hard Grader 评分和渐进式重试的对话方法。

**参数**:
- `query` (str): 用户问题
- `max_retries` (int): 最大重试次数，默认 3

**返回值**:
- `str`: 最终答案
- `List[dict]`: 评分历史，每条包含:
  - `attempt`: 尝试次数
  - `limit`: 该轮 search_memory 的 limit 值
  - `answer`: 答案前 200 字符
  - `grade`: 完整评分结果
  - `passed`: 是否通过
  - `fail_reason`: 失败原因
  - `tool_calls`: 工具调用次数

**行为**:
- 渐进式 limit 扩展: 5 → 8 → 12
- 通过条件:
  - `depth >= 10` (硬性门槛)
  - `citation >= 5` (硬性门槛)
  - `evidence >= 10` (硬性门槛)
  - `score >= 70` (总分阈值)
- 失败时使用 Refiner (主模型) 生成新查询建议
- Refiner 建议作为 hint 注入下一轮 prompt

---

### 2. `chat_verbose(query) -> str`

带实时日志的对话方法，输出完整的 Thought → Action → Observation 链。

**参数**:
- `query` (str): 用户问题

**返回值**:
- `str`: Agent 回答

**行为**:
- 保留对话上下文 (多轮)
- 实时打印 AgentStream 事件 (推理链增量)
- 打印 ToolCallResult 事件 (工具名、参数、输出前 300 字符)
- 不进行评分

**用途**: 调试 ReAct 推理过程，观察工具选择逻辑

---

### 3. `chat(query) -> str`

标准多轮对话，保持上下文。

**参数**:
- `query` (str): 用户问题

**返回值**:
- `str`: Agent 回答

**行为**:
- 保留对话上下文
- 使用 `self._ctx` (Context) 维护状态
- 静默执行，最小化日志

**用途**: 常规对话场景

---

### 4. `run(query) -> str`

无状态单次查询。

**参数**:
- `query` (str): 用户问题

**返回值**:
- `str`: Agent 回答

**行为**:
- 不保留上下文，每次查询独立
- 最简单的执行模式

**用途**: 一次性查询

---

## 辅助方法

### `reset_context()`

重置对话上下文，开启新会话。

```python
agent.reset_context()
# 之后的 chat() 调用将不记得之前的对话
```

---

## 工厂函数

### `create_agent(session_id="default", model=None, verbose=False, enable_grader=True)`

快捷创建 Agent 实例。

```python
from src.agent import create_agent

agent = create_agent(
    session_id="test-001",
    model="gemini-3-pro-preview",
    verbose=True,
    enable_grader=True
)
```

---

## 使用示例

### 命令行

```bash
# 质量保证模式 (带评分和重试)
python -m src.scripts.run_agent -g "少女是如何重回世界的"

# 调试模式 (查看推理链)
python -m src.scripts.run_agent -v "努昂诺塔和少女是什么关系"

# 交互模式 (多轮对话)
python -m src.scripts.run_agent -i

# 简单查询
python -m src.scripts.run_agent "玛薇卡是谁"
```

### 代码调用

```python
import asyncio
from src.agent import create_agent

async def main():
    agent = create_agent()

    # 方式 1: 带评分
    answer, history = await agent.chat_with_grading("少女是如何重回世界的")
    print(f"通过: {history[-1]['passed']}")

    # 方式 2: 调试
    answer = await agent.chat_verbose("描述竞技场的战斗")

    # 方式 3: 多轮对话
    answer1 = await agent.chat("基尼奇是谁")
    answer2 = await agent.chat("他的同伴是谁")  # 记得上下文

    # 方式 4: 单次查询
    answer = await agent.run("火神的称号是什么")

asyncio.run(main())
```

---

## 评分系统

Hard Grader 使用 5 个维度评分 (每个 0-20 分):

| 维度 | 说明 | 硬性门槛 |
|------|------|----------|
| tool_usage | 是否调用了适当的工具 | - |
| evidence | 答案是否基于工具返回的证据 | >= 10 |
| completeness | 是否完整回答了问题 | - |
| citation | 是否引用了来源 (Chapter/Task ID) | >= 5 |
| depth | 答案深度 (关系类问题需要具体事件) | >= 10 |

**通过条件**: `depth >= 10 AND citation >= 5 AND evidence >= 10 AND score >= 70`
