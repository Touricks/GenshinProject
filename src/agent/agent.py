"""
Genshin Retrieval Agent using LlamaIndex ReActAgent.

This module provides the main ReAct agent that orchestrates
tool calls to the Knowledge Graph and Vector Database.
Features:
- Explicit Thought → Action → Observation reasoning chain
- Hard Grader for answer quality evaluation
- Progressive limit expansion for search_memory
"""

import logging
import os
import re
import time
from typing import Optional, List, Tuple, Dict, Any

from ..config import Settings
from .prompts import SYSTEM_PROMPT
from .tracer import AgentTracer

logger = logging.getLogger(__name__)

# Progressive limit expansion for search_memory (3 rounds)
# 广度优先策略：每次少量精确结果 + 多工具组合
LIMIT_PROGRESSION = {
    1: 3,  # 第1轮 - 少量精确结果
    2: 5,  # 第2轮 - 继续少量
    3: 8,  # 第3轮 - 略微扩大
}


def _ensure_google_api_key():
    """
    Ensure GOOGLE_API_KEY is set in environment.

    The google-genai library looks for GOOGLE_API_KEY, but users might
    have GEMINI_API_KEY instead. This function copies the value if needed.
    """
    if not os.environ.get("GOOGLE_API_KEY"):
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            os.environ["GOOGLE_API_KEY"] = gemini_key
            logger.debug("Copied GEMINI_API_KEY to GOOGLE_API_KEY")


class GenshinRetrievalAgent:
    """
    ReAct Agent for Genshin Story QA.

    Uses LlamaIndex ReActAgent with:
    - Google Gemini LLM for reasoning
    - Explicit Thought → Action → Observation chain
    - Hard Grader for answer quality evaluation
    - Progressive limit expansion for retries
    """

    def __init__(
        self,
        session_id: str = "default",
        model: str = None,
        verbose: bool = False,
        enable_grader: bool = True,
    ):
        """
        Initialize the Genshin Retrieval Agent.

        Args:
            session_id: Unique session identifier for memory persistence.
            model: LLM model name (default from settings).
            verbose: Whether to log tool calls.
            enable_grader: Whether to enable answer quality grading.
        """
        self.session_id = session_id
        self.verbose = verbose
        self.enable_grader = enable_grader
        self.settings = Settings()
        self.model = model or self.settings.REASONING_MODEL

        # Lazy initialization
        self._agent = None
        self._ctx = None
        self._memory = None
        self._llm = None
        self._grader = None
        self._grader_llm = None  # Separate fast LLM for grader/refiner
        self._refiner = None
        self._current_limit = 5  # Default limit for search_memory
        self._tracer = AgentTracer()  # Full chain tracer for debugging
        self._pending_context_summary = None  # 用于在下一轮 trace 中记录上下文

    def _ensure_initialized(self):
        """Ensure the agent is initialized (lazy loading)."""
        if self._agent is not None:
            return

        # Ensure GOOGLE_API_KEY is set (may copy from GEMINI_API_KEY)
        _ensure_google_api_key()

        logger.info(f"Initializing GenshinRetrievalAgent with model: {self.model}")

        # Import LlamaIndex components
        try:
            from llama_index.core.agent.workflow import ReActAgent
            from llama_index.core.memory import Memory
            from llama_index.core.workflow import Context
            from llama_index.llms.google_genai import GoogleGenAI
        except ImportError as e:
            raise ImportError(
                f"Missing required packages. Install with:\n"
                f"pip install llama-index-llms-google-genai google-genai\n"
                f"Original error: {e}"
            )

        # Import tools with dynamic limit wrapper
        from ..retrieval import (
            lookup_knowledge,
            find_connection,
            track_journey,
            get_character_events,
        )
        from ..retrieval.search_memory import search_memory as _search_memory

        # Create a wrapper for search_memory that uses current_limit
        def search_memory_with_limit(
            query: str,
            characters: Optional[str] = None,
            sort_by: str = "relevance",
        ) -> str:
            """
            Search the story text for specific plot details, dialogues, or events.
            This is the ONLY tool that returns actual story content (text chunks).

            Args:
                query: Search keywords (supports Chinese). Use specific terms for better results.
                characters: Optional character name to filter results (e.g., "少女", "旅行者").
                sort_by: Sort order - "relevance" (default, best matches first) or "time" (chronological).

            Returns:
                Formatted string with matching story chunks including chapter, task ID, and dialogue content.

            Note: Result count is controlled by the system based on retry attempts.
            """
            return _search_memory(
                query=query,
                characters=characters,
                sort_by=sort_by,
                limit=self._current_limit,
            )

        # Initialize LLM
        # Disable AFC (Automated Function Calling) to let ReActAgent
        # handle tool calling through text-based prompting
        from google.genai import types as genai_types

        self._llm = GoogleGenAI(
            model=self.model,
            is_function_calling_model=False,
            generation_config=genai_types.GenerateContentConfig(
                automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(
                    disable=True
                )
            ),
        )

        # Initialize Memory
        self._memory = Memory.from_defaults(
            session_id=self.session_id,
            token_limit=8000,
            chat_history_token_ratio=0.7,
        )

        # Initialize ReActAgent with tools
        self._agent = ReActAgent(
            tools=[
                lookup_knowledge,
                find_connection,
                track_journey,
                search_memory_with_limit,
                get_character_events,  # NEW: Major events for abstract queries
            ],
            llm=self._llm,
            system_prompt=SYSTEM_PROMPT,
        )

        # Initialize Context for multi-turn
        self._ctx = Context(self._agent)

        # Initialize Grader and Refiner with fast LLM if enabled
        if self.enable_grader:
            from .grader import AnswerGrader
            from .refiner import QueryRefiner

            # Use a separate fast LLM for grader/refiner (speed priority)
            self._grader_llm = GoogleGenAI(
                model=self.settings.GRADER_MODEL,  # gemini-2.5-flash by default
                is_function_calling_model=False,
            )
            logger.info(f"Grader/Refiner using fast model: {self.settings.GRADER_MODEL}")

            self._grader = AnswerGrader(self._grader_llm)
            # Refiner 也使用快速模型（查询分解不需要强推理）
            self._refiner = QueryRefiner(self._grader_llm)

        logger.info("GenshinRetrievalAgent initialized successfully (ReActAgent mode)")

    def _set_search_limit(self, limit: int):
        """Set the current limit for search_memory tool."""
        self._current_limit = limit
        logger.debug(f"search_memory limit set to {limit}")

    def _summarize_tool_output(self, tool: str, output: str) -> str:
        """提取 tool output 的结论摘要，不包含 chunk 原文。"""
        if tool == "find_connection":
            # 提取关系类型，如 "PARTNER_OF"
            match = re.search(r'-\[(\w+)\]->', output)
            return match.group(1) if match else "已找到关系"
        elif tool in ("search_memory", "search_memory_with_limit"):
            # 只返回结果数量，不返回 chunk 内容
            result_count = output.count("### 结果")
            return f"返回 {result_count} 个相关片段"
        elif tool == "lookup_knowledge":
            return "已返回实体信息"
        elif tool == "get_character_events":
            # 提取事件数量
            event_count = output.count("**")
            return f"返回 {event_count // 2} 个事件"
        elif tool == "track_journey":
            return "已返回时间线"
        else:
            return "已执行"

    def _build_attempt_context(self, attempt_data: Dict[str, Any]) -> str:
        """构建上一轮尝试的 Markdown 上下文。"""
        # 构建工具调用摘要
        tool_calls_md = []
        for tc in attempt_data.get("tool_calls", []):
            summary = self._summarize_tool_output(tc["tool"], tc["output"])
            kwargs_str = ", ".join(f"{k}={v}" for k, v in tc["kwargs"].items())
            tool_calls_md.append(f"- **{tc['tool']}**({kwargs_str}) → {summary}")

        grade = attempt_data.get("grade", {})
        scores = grade.get("scores", {})
        refiner = attempt_data.get("refiner_queries", [])

        # 截断答案
        answer = attempt_data.get("answer", "")
        if len(answer) > 150:
            answer = answer[:150] + "..."

        return f"""## 上一轮尝试 (Attempt {attempt_data['attempt']})

### 工具调用
{chr(10).join(tool_calls_md) if tool_calls_md else "(无)"}

### 回答
{answer}

### 评分结果
- 总分: {grade.get('score', 0)}/100, 深度: {scores.get('depth', 0)}/20
- 失败原因: {grade.get('fail_reason', '')}
- 改进建议: {grade.get('suggestion', '')}

### Refiner 建议搜索
{', '.join(f'"{q}"' for q in refiner) if refiner else '(无)'}
"""

    async def _humanize_response(self, response: str) -> str:
        """去引用处理，使回答更自然。

        Args:
            response: Agent 的原始回答（可能包含引用标注）。

        Returns:
            更自然的回答，移除了引用标注。
        """
        prompt = """你是一个文本改写助手。请将以下回答改写，移除学术化的引用格式。

要求：
1. 移除所有"(第X章，任务XXXX)"、"根据第X章"等引用标注
2. 保留所有具体信息、对话原文和事件细节
3. 使用平实、自然的中文表达，不要过于口语化或浮夸
4. 不要添加"没问题"、"我来"等开场白，直接输出改写后的内容
5. 保持原文的结构和层次

原回答：
{response}

直接输出改写后的内容："""

        try:
            result = await self._llm.acomplete(prompt.format(response=response))
            humanized = str(result).strip()
            logger.debug(f"Humanized response: {len(response)} -> {len(humanized)} chars")
            return humanized
        except Exception as e:
            logger.warning(f"Humanize failed: {e}, returning original")
            return response

    async def run(self, query: str) -> str:
        """
        Run a single query (stateless).

        Args:
            query: User question.

        Returns:
            Agent response as string.
        """
        self._ensure_initialized()

        logger.info(f"Running query: {query[:50]}...")

        response = await self._agent.run(user_msg=query)
        return str(response)

    async def chat(self, query: str) -> str:
        """
        Run a multi-turn chat query (preserves context).

        Args:
            query: User question.

        Returns:
            Agent response as string.
        """
        self._ensure_initialized()

        logger.info(f"Chat query: {query[:50]}...")

        response = await self._agent.run(user_msg=query, ctx=self._ctx)
        return str(response)

    async def chat_verbose(self, query: str) -> str:
        """
        Run a multi-turn chat with Thought/Action/Observation logging.

        Args:
            query: User question.

        Returns:
            Agent response as string.
        """
        self._ensure_initialized()

        from llama_index.core.agent.workflow import ToolCallResult, AgentStream

        logger.info(f"Verbose chat query: {query[:50]}...")

        handler = self._agent.run(query, ctx=self._ctx)

        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                # Print ReAct reasoning (Thought, Action, Answer)
                print(f"{event.delta}", end="", flush=True)
            elif isinstance(event, ToolCallResult):
                tool_name = event.tool_name
                tool_kwargs = event.tool_kwargs
                tool_output = str(event.tool_output)[:300]
                print(f"\n[Observation] {tool_name}({tool_kwargs})")
                print(f"  → {tool_output}...")
                print()

        response = await handler
        return str(response)

    async def chat_with_grading(
        self,
        query: str,
        max_retries: int = 3,
    ) -> Tuple[str, List[dict]]:
        """
        Run a chat query with Hard Grader evaluation.

        Progressive expansion: Each retry increases search_memory limit.

        Pass criteria:
        - depth >= 10 (硬性门槛)
        - total score >= 70

        Args:
            query: User question.
            max_retries: Maximum number of retry attempts (default: 2).

        Returns:
            Tuple of (final_answer, grading_history)
        """
        self._ensure_initialized()

        if not self._grader:
            logger.warning("Grader not enabled, falling back to simple chat")
            return await self.chat(query), []

        from llama_index.core.agent.workflow import ToolCallResult, AgentStream

        # Start trace
        start_time = time.time()
        self._tracer.start_trace(query, {
            "agent_model": self.model,
            "grader_model": self.settings.GRADER_MODEL,
            "max_retries": max_retries,
        })

        grading_history = []
        attempts_history = []  # 结构化历史，用于上下文传递
        current_query = query
        tool_calls_history = []
        answer = ""
        passed = False
        self._pending_context_summary = None  # 重置上下文摘要

        for attempt in range(1, max_retries + 1):
            # Set progressive limit
            current_limit = LIMIT_PROGRESSION.get(attempt, 5)
            self._set_search_limit(current_limit)

            logger.info(f"Attempt {attempt}/{max_retries} with limit={current_limit}")

            # Start attempt trace (记录发送给 Agent 的完整 query)
            self._tracer.start_attempt(attempt, current_limit, input_query=current_query)

            # 如果有上一轮的上下文摘要，记录到当前 attempt
            if self._pending_context_summary is not None:
                self._tracer.log_context_injection(self._pending_context_summary)
                self._pending_context_summary = None

            # Run ReAct agent
            handler = self._agent.run(current_query, ctx=self._ctx)

            # Collect tool calls and reasoning stream
            attempt_tool_calls = []
            async for event in handler.stream_events():
                if isinstance(event, ToolCallResult):
                    tool_output = str(event.tool_output)
                    # 增加截断长度到 2000 字符，确保完整的 chunk 内容不被截断
                    # 之前 500 字符导致关键证据（如角色死亡对话）被截断
                    attempt_tool_calls.append({
                        "tool": event.tool_name,
                        "kwargs": event.tool_kwargs,
                        "output": tool_output[:2000],
                    })
                    # Log tool call to tracer
                    self._tracer.log_tool_call(
                        tool=event.tool_name,
                        input_data=event.tool_kwargs,
                        output=tool_output,
                    )
                elif isinstance(event, AgentStream):
                    # Log reasoning stream
                    self._tracer.log_reasoning_stream(event.delta)

            response = await handler
            answer = str(response)
            tool_calls_history.extend(attempt_tool_calls)

            # Grade the answer
            grade_start = time.time()
            grade_result = await self._grader.grade(
                question=query,
                answer=answer,
                tool_calls=attempt_tool_calls,
            )
            grade_duration = int((time.time() - grade_start) * 1000)

            # Log grading to tracer
            self._tracer.log_grading(
                input_data={
                    "question": query,
                    "answer": answer,
                    "tool_calls": attempt_tool_calls,
                },
                output=grade_result,
                duration_ms=grade_duration,
            )

            grading_history.append({
                "attempt": attempt,
                "limit": current_limit,
                "answer": answer[:200] + "..." if len(answer) > 200 else answer,
                "grade": grade_result,
                "passed": grade_result.get("passed", False),
                "fail_reason": grade_result.get("fail_reason"),
                "tool_calls": len(attempt_tool_calls),
            })

            # Log grade result with pass/fail info
            passed = grade_result.get("passed", False)
            fail_reason = grade_result.get("fail_reason", "")
            logger.info(
                f"Grade: {grade_result['score']}/100, "
                f"depth={grade_result.get('scores', {}).get('depth', 0)}, "
                f"passed={passed}"
                + (f" ({fail_reason})" if fail_reason else "")
            )

            # Check if passed (uses hard threshold logic from grader)
            if passed:
                logger.info(f"Passed grading on attempt {attempt}")
                # End attempt trace before break
                self._tracer.end_attempt(answer)
                break

            # Prepare for retry with Refiner suggestions
            if attempt < max_retries:
                suggestion = grade_result.get("suggestion", "请提供更详细的答案")

                # Use Refiner to decompose the query
                refined_queries = []
                if self._refiner:
                    try:
                        refiner_start = time.time()
                        refined_queries = await self._refiner.refine(query, suggestion)
                        refiner_duration = int((time.time() - refiner_start) * 1000)
                        logger.info(f"Refiner generated queries: {refined_queries}")

                        # Log refiner to tracer (before end_attempt!)
                        self._tracer.log_refiner(
                            question=query,
                            suggestion=suggestion,
                            queries=refined_queries,
                            duration_ms=refiner_duration,
                        )
                    except Exception as e:
                        logger.warning(f"Refiner failed: {e}")

                # 收集本轮数据用于结构化上下文
                attempt_data = {
                    "attempt": attempt,
                    "tool_calls": attempt_tool_calls,
                    "answer": answer,
                    "grade": grade_result,
                    "refiner_queries": refined_queries,
                }
                attempts_history.append(attempt_data)

                # End attempt trace after refiner logging
                self._tracer.end_attempt(answer)

                # 构建结构化历史上下文
                history_context = "\n---\n".join(
                    self._build_attempt_context(a) for a in attempts_history
                )

                # 构建重试 prompt，包含完整历史上下文
                queries_hint = ", ".join(f'"{q}"' for q in refined_queries) if refined_queries else ""
                current_query = f"""{history_context}

---

## 当前任务
{query}

**重要**: 根据上述历史：
1. 不要重复调用已经调用过的工具（结果相同）
2. 必须调用 search_memory 获取故事原文增加深度
{f"3. 建议搜索关键词: {queries_hint}" if queries_hint else ""}
"""

                # Reset context for fresh attempt
                self.reset_context()

                # 为下一轮的 trace 准备上下文摘要
                # (会在下一轮 start_attempt 后立即记录)
                self._pending_context_summary = {
                    "from_attempts": [a["attempt"] for a in attempts_history],
                    "last_tool_summary": self._summarize_tool_output(
                        attempt_tool_calls[0]["tool"],
                        attempt_tool_calls[0]["output"]
                    ) if attempt_tool_calls else None,
                    "last_grade_summary": {
                        "score": grade_result.get("score"),
                        "depth": grade_result.get("scores", {}).get("depth"),
                        "fail_reason": grade_result.get("fail_reason"),
                    },
                    "refiner_queries": refined_queries,
                }
            else:
                # Last attempt, just end trace
                self._tracer.end_attempt(answer)

        # 只在通过时去引用，失败的回答保留原格式用于调试
        humanized = None
        if passed:
            humanized = await self._humanize_response(answer)

        # End trace and save to file (保存原格式和去引用后两种回答)
        total_duration = int((time.time() - start_time) * 1000)
        trace_path = self._tracer.end_trace(
            final_response=answer,  # 原格式
            passed=passed,
            total_duration_ms=total_duration,
            humanized_response=humanized,  # 去引用后
        )
        if trace_path:
            logger.info(f"Trace saved: {trace_path}")

        if not passed:
            logger.warning(f"Max retries ({max_retries}) reached, returning last answer")

        # 返回去引用后的回答（如果有）
        return humanized if humanized else answer, grading_history

    def reset_context(self):
        """Reset the conversation context for a new session."""
        if self._agent is not None:
            from llama_index.core.workflow import Context
            self._ctx = Context(self._agent)
            logger.info("Conversation context reset")


# Factory function for easy instantiation
def create_agent(
    session_id: str = "default",
    model: str = None,
    verbose: bool = False,
    enable_grader: bool = True,
) -> GenshinRetrievalAgent:
    """
    Create a Genshin Retrieval Agent.

    Args:
        session_id: Unique session identifier.
        model: LLM model name.
        verbose: Whether to enable verbose logging.
        enable_grader: Whether to enable answer quality grading.

    Returns:
        Configured GenshinRetrievalAgent instance.
    """
    return GenshinRetrievalAgent(
        session_id=session_id,
        model=model,
        verbose=verbose,
        enable_grader=enable_grader,
    )
