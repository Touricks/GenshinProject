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
from typing import Optional, List, Tuple

from ..config import Settings
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Progressive limit expansion for search_memory
LIMIT_PROGRESSION = {
    1: 5,   # 第1次：默认 limit=5
    2: 8,   # 第2次：扩大到 8
    3: 12,  # 第3次：扩大到 12
    4: 15,  # 第4次：扩大到 15
    5: 20,  # 第5次：最大 20
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
        self.model = model or self.settings.LLM_MODEL

        # Lazy initialization
        self._agent = None
        self._ctx = None
        self._memory = None
        self._llm = None
        self._grader = None
        self._current_limit = 5  # Default limit for search_memory

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
            """
            return _search_memory(
                query=query,
                characters=characters,
                sort_by=sort_by,
                limit=self._current_limit,
            )

        # Copy docstring for LLM to understand the tool
        search_memory_with_limit.__doc__ = _search_memory.__doc__

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
            ],
            llm=self._llm,
            system_prompt=SYSTEM_PROMPT,
        )

        # Initialize Context for multi-turn
        self._ctx = Context(self._agent)

        # Initialize Grader if enabled
        if self.enable_grader:
            from .grader import AnswerGrader
            self._grader = AnswerGrader(self._llm)

        logger.info("GenshinRetrievalAgent initialized successfully (ReActAgent mode)")

    def _set_search_limit(self, limit: int):
        """Set the current limit for search_memory tool."""
        self._current_limit = limit
        logger.debug(f"search_memory limit set to {limit}")

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
        max_retries: int = 5,
    ) -> Tuple[str, List[dict]]:
        """
        Run a chat query with Hard Grader evaluation.

        Progressive expansion: Each retry increases search_memory limit.

        Pass criteria:
        - depth >= 10 (硬性门槛)
        - total score >= 70

        Args:
            query: User question.
            max_retries: Maximum number of retry attempts (default: 5).

        Returns:
            Tuple of (final_answer, grading_history)
        """
        self._ensure_initialized()

        if not self._grader:
            logger.warning("Grader not enabled, falling back to simple chat")
            return await self.chat(query), []

        from llama_index.core.agent.workflow import ToolCallResult

        grading_history = []
        current_query = query
        tool_calls_history = []

        for attempt in range(1, max_retries + 1):
            # Set progressive limit
            current_limit = LIMIT_PROGRESSION.get(attempt, 20)
            self._set_search_limit(current_limit)

            logger.info(f"Attempt {attempt}/{max_retries} with limit={current_limit}")

            # Run ReAct agent
            handler = self._agent.run(current_query, ctx=self._ctx)

            # Collect tool calls
            attempt_tool_calls = []
            async for event in handler.stream_events():
                if isinstance(event, ToolCallResult):
                    attempt_tool_calls.append({
                        "tool": event.tool_name,
                        "kwargs": event.tool_kwargs,
                        "output": str(event.tool_output)[:500],
                    })

            response = await handler
            answer = str(response)
            tool_calls_history.extend(attempt_tool_calls)

            # Grade the answer
            grade_result = await self._grader.grade(
                question=query,
                answer=answer,
                tool_calls=attempt_tool_calls,
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
                return answer, grading_history

            # Prepare for retry with suggestions
            if attempt < max_retries:
                suggestion = grade_result.get("suggestion", "请提供更详细的答案")
                next_limit = LIMIT_PROGRESSION.get(attempt + 1, 20)
                current_query = (
                    f"{query}\n\n"
                    f"[系统提示: 上次答案不完整 (尝试 {attempt}/{max_retries}). "
                    f"改进建议: {suggestion}. "
                    f"已扩大搜索范围到 limit={next_limit}]"
                )
                # Reset context for fresh attempt
                self.reset_context()

        logger.warning(f"Max retries ({max_retries}) reached, returning last answer")
        return answer, grading_history

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
