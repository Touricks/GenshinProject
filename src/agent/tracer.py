"""Agent Tracer for full chain logging.

Captures the complete execution trace of the ReAct agent including:
- Database queries (Neo4j, Qdrant) with inputs/outputs
- LLM reasoning chain (Thought/Action/Observation)
- Grader and Refiner workflow details
- Timing information for performance analysis
"""

import json
import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# 正则模式用于解析 ReAct 输出
# Thought: <text> (直到遇到 Action, Thought, 或 Answer)
THOUGHT_PATTERN = re.compile(r'Thought:\s*(.+?)(?=\n(?:Action|Thought|Answer)|$)', re.DOTALL)
# Action: <tool_name>
ACTION_PATTERN = re.compile(r'Action:\s*(\w+)')
# Action Input: {<json>} - 使用非贪婪匹配到闭合括号
ACTION_INPUT_PATTERN = re.compile(r'Action Input:\s*(\{[^}]*\})')


class AgentTracer:
    """Captures full trace of agent execution for debugging.

    Usage:
        tracer = AgentTracer()
        tracer.start_trace(query, config)
        tracer.start_attempt(1, limit=5)
        tracer.log_tool_call("search_memory", {...}, "result...")
        tracer.log_grading({...}, {...})
        tracer.end_attempt(response)
        tracer.end_trace(final_response, passed=True, total_duration_ms=40000)
    """

    def __init__(self, log_dir: str = "logger/traces"):
        """Initialize tracer with log directory.

        Args:
            log_dir: Directory to store trace JSON files.
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_trace: Optional[Dict[str, Any]] = None
        self.current_attempt: Optional[Dict[str, Any]] = None
        self._reasoning_buffer: str = ""  # Buffer for streaming reasoning

    def start_trace(self, query: str, config: Dict[str, Any]) -> str:
        """Start a new trace for a query.

        Args:
            query: The user's question.
            config: Agent configuration (models, max_retries, etc.)

        Returns:
            Trace ID in format: {timestamp}-{query_hash}
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        query_hash = hashlib.md5(query.encode()).hexdigest()[:6]
        trace_id = f"{timestamp}-{query_hash}"

        self.current_trace = {
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "config": config,
            "attempts": [],
            "final_response": None,
            "total_duration_ms": 0,
            "passed": False,
        }

        logger.info(f"[Tracer] Started trace: {trace_id}")
        return trace_id

    def start_attempt(self, attempt: int, limit: int, input_query: str = None):
        """Start tracking a new attempt.

        Args:
            attempt: Attempt number (1-based).
            limit: Current search_memory limit.
            input_query: The actual query sent to the agent (may include injected context).
        """
        self.current_attempt = {
            "attempt": attempt,
            "limit": limit,
            "input_query": input_query,  # 记录发送给 Agent 的完整 query
            "context_from_previous": None,  # 上下文摘要（由 log_context_injection 填充）
            "tool_calls": [],
            "reasoning": {
                "raw_stream": "",  # Full reasoning stream
                "thoughts": [],
                "actions": [],
                "observations": [],
            },
            "response": None,
            "grading": None,
            "refiner": None,
            "start_time": datetime.now().isoformat(),
        }
        self._reasoning_buffer = ""
        logger.debug(f"[Tracer] Started attempt {attempt} with limit={limit}")

    def log_context_injection(self, context_summary: Dict[str, Any]):
        """Log the structured context injected from previous attempts.

        Args:
            context_summary: Summary of what was injected, e.g.:
                {
                    "from_attempt": 1,
                    "tool_summary": "find_connection → PARTNER_OF",
                    "grade_summary": {"score": 65, "depth": 5},
                    "refiner_queries": [...]
                }
        """
        if self.current_attempt is None:
            return
        self.current_attempt["context_from_previous"] = context_summary
        logger.debug(f"[Tracer] Context injected from attempts {context_summary.get('from_attempts')}")

    def log_tool_call(
        self,
        tool: str,
        input_data: Dict[str, Any],
        output: str,
        results: Any = None,
        duration_ms: int = 0,
    ):
        """Log a tool call with input/output.

        Args:
            tool: Tool name (e.g., "search_memory", "find_connection").
            input_data: Tool input parameters.
            output: Tool output string.
            results: Raw results data (optional, for detailed logging).
            duration_ms: Execution time in milliseconds.
        """
        if self.current_attempt is None:
            return

        # Truncate long outputs for readability
        # 增加到 6000 字符以保留完整的 chunk 内容
        output_truncated = output[:6000] + "..." if len(output) > 6000 else output

        tool_call = {
            "tool": tool,
            "input": input_data,
            "output": output_truncated,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        }

        # Include raw results if provided (for detailed analysis)
        if results is not None:
            # Limit results size to prevent huge log files
            if isinstance(results, list) and len(results) > 10:
                tool_call["results_count"] = len(results)
                tool_call["results_sample"] = results[:5]
            else:
                tool_call["results"] = results

        self.current_attempt["tool_calls"].append(tool_call)
        logger.debug(f"[Tracer] Tool call: {tool}({input_data}) -> {len(output)} chars")

    def log_reasoning_stream(self, delta: str):
        """Log streaming reasoning output from ReAct agent.

        Args:
            delta: Incremental text from agent stream.
        """
        if self.current_attempt is None:
            return

        self._reasoning_buffer += delta
        self.current_attempt["reasoning"]["raw_stream"] = self._reasoning_buffer

    def log_reasoning(
        self,
        thought: str = None,
        action: str = None,
        observation: str = None,
    ):
        """Log structured reasoning components.

        Args:
            thought: Agent's thought/reasoning text.
            action: Tool action taken.
            observation: Tool observation/result.
        """
        if self.current_attempt is None:
            return

        reasoning = self.current_attempt["reasoning"]

        if thought:
            reasoning["thoughts"].append(thought)
        if action:
            reasoning["actions"].append(action)
        if observation:
            obs_truncated = observation[:500] + "..." if len(observation) > 500 else observation
            reasoning["observations"].append(obs_truncated)

    def log_grading(
        self,
        input_data: Dict[str, Any],
        output: Dict[str, Any],
        duration_ms: int = 0,
    ):
        """Log grader input and output.

        Args:
            input_data: Data sent to grader (question, answer, tool_calls).
            output: Grader response (scores, reason, suggestion, passed).
            duration_ms: Grading execution time.
        """
        if self.current_attempt is None:
            return

        # Truncate answer in input for readability
        input_copy = input_data.copy()
        if "answer" in input_copy and len(input_copy["answer"]) > 500:
            input_copy["answer"] = input_copy["answer"][:500] + "..."

        self.current_attempt["grading"] = {
            "input": input_copy,
            "output": output,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        }

        logger.debug(
            f"[Tracer] Grading: score={output.get('score')}, "
            f"depth={output.get('scores', {}).get('depth')}, "
            f"passed={output.get('passed')}"
        )

    def log_refiner(
        self,
        question: str,
        suggestion: str,
        queries: List[str],
        duration_ms: int = 0,
    ):
        """Log refiner input and output.

        Args:
            question: Original user question.
            suggestion: Grader's improvement suggestion.
            queries: List of refined search queries.
            duration_ms: Refiner execution time.
        """
        if self.current_attempt is None:
            return

        self.current_attempt["refiner"] = {
            "input": {
                "question": question,
                "suggestion": suggestion,
            },
            "output": {
                "queries": queries,
            },
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        }

        logger.debug(f"[Tracer] Refiner generated {len(queries)} queries: {queries}")

    def _parse_reasoning(self, raw_stream: str) -> Dict[str, List[str]]:
        """解析 raw_stream 中的结构化推理组件。

        Args:
            raw_stream: ReAct agent 的原始输出流。

        Returns:
            包含 thoughts, actions, observations 的字典。
        """
        thoughts = THOUGHT_PATTERN.findall(raw_stream)
        actions = ACTION_PATTERN.findall(raw_stream)
        action_inputs = ACTION_INPUT_PATTERN.findall(raw_stream)

        # 去重：LLM 可能在流式输出中重复输出相同的 Action
        # 保留唯一的 (action, input) 对
        seen = set()
        unique_actions = []
        unique_inputs = []
        for i, action in enumerate(actions):
            action_input = action_inputs[i] if i < len(action_inputs) else ""
            key = (action, action_input)
            if key not in seen:
                seen.add(key)
                unique_actions.append(action)
                if action_input:
                    unique_inputs.append(action_input)

        return {
            "thoughts": [t.strip() for t in thoughts if t.strip()],
            "actions": unique_actions,
            "observations": unique_inputs,
        }

    def end_attempt(self, response: str):
        """End current attempt and add to trace.

        Args:
            response: Agent's response for this attempt.
        """
        if self.current_attempt is None or self.current_trace is None:
            return

        # 解析 raw_stream 填充结构化字段
        raw_stream = self.current_attempt["reasoning"]["raw_stream"]
        parsed = self._parse_reasoning(raw_stream)
        self.current_attempt["reasoning"]["thoughts"] = parsed["thoughts"]
        self.current_attempt["reasoning"]["actions"] = parsed["actions"]
        self.current_attempt["reasoning"]["observations"] = parsed["observations"]

        self.current_attempt["response"] = response
        self.current_attempt["end_time"] = datetime.now().isoformat()
        self.current_trace["attempts"].append(self.current_attempt)

        logger.debug(
            f"[Tracer] Ended attempt {self.current_attempt['attempt']} "
            f"with {len(self.current_attempt['tool_calls'])} tool calls"
        )
        self.current_attempt = None
        self._reasoning_buffer = ""

    def end_trace(
        self,
        final_response: str,
        passed: bool,
        total_duration_ms: int,
        humanized_response: str = None,
    ) -> str:
        """End trace and save to file.

        Args:
            final_response: Final answer returned to user (原格式，带引用).
            passed: Whether grading passed.
            total_duration_ms: Total execution time.
            humanized_response: Optional humanized answer (去引用后).

        Returns:
            Path to saved trace file.
        """
        if self.current_trace is None:
            return ""

        self.current_trace["final_response"] = final_response
        self.current_trace["humanized_response"] = humanized_response  # 去引用后的回答
        self.current_trace["passed"] = passed
        self.current_trace["total_duration_ms"] = total_duration_ms
        self.current_trace["end_timestamp"] = datetime.now().isoformat()

        # Save to file
        trace_id = self.current_trace["trace_id"]
        filepath = self.log_dir / f"{trace_id}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.current_trace, f, ensure_ascii=False, indent=2)

        logger.info(
            f"[Tracer] Trace saved: {filepath} "
            f"(passed={passed}, duration={total_duration_ms}ms)"
        )

        self.current_trace = None
        return str(filepath)

    def get_current_trace(self) -> Optional[Dict[str, Any]]:
        """Get current trace data (for debugging).

        Returns:
            Current trace dict or None if no active trace.
        """
        return self.current_trace
