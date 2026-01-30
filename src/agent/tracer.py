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
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


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

    def start_attempt(self, attempt: int, limit: int):
        """Start tracking a new attempt.

        Args:
            attempt: Attempt number (1-based).
            limit: Current search_memory limit.
        """
        self.current_attempt = {
            "attempt": attempt,
            "limit": limit,
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
        output_truncated = output[:1000] + "..." if len(output) > 1000 else output

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

    def end_attempt(self, response: str):
        """End current attempt and add to trace.

        Args:
            response: Agent's response for this attempt.
        """
        if self.current_attempt is None or self.current_trace is None:
            return

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
    ) -> str:
        """End trace and save to file.

        Args:
            final_response: Final answer returned to user.
            passed: Whether grading passed.
            total_duration_ms: Total execution time.

        Returns:
            Path to saved trace file.
        """
        if self.current_trace is None:
            return ""

        self.current_trace["final_response"] = final_response
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
