"""Tests for the AnswerGrader class."""
import pytest
from unittest.mock import MagicMock, AsyncMock


class TestUnknownConclusionDetection:
    """Test cases for _is_unknown_conclusion_async() method."""

    @pytest.fixture
    def grader(self):
        """Create a grader with mock LLM."""
        from src.agent.grader import AnswerGrader
        mock_llm = MagicMock()
        return AnswerGrader(mock_llm)

    @pytest.fixture
    def grader_with_async_llm(self):
        """Create a grader with async mock LLM."""
        from src.agent.grader import AnswerGrader
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock()
        return AnswerGrader(mock_llm)

    @pytest.mark.asyncio
    async def test_detects_no_answer(self, grader_with_async_llm):
        """Test detection when LLM says NO_ANSWER."""
        grader_with_async_llm.llm.acomplete.return_value = "NO_ANSWER"
        result = await grader_with_async_llm._is_unknown_conclusion_async(
            "问题",
            "少女表示她不知道那首摇篮曲是谁唱的。"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_passes_has_answer(self, grader_with_async_llm):
        """Test that HAS_ANSWER passes through."""
        grader_with_async_llm.llm.acomplete.return_value = "HAS_ANSWER"
        result = await grader_with_async_llm._is_unknown_conclusion_async(
            "问题",
            "摇篮曲实际上是她自己唱的，这形成了一个时间闭环。"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_handles_answer_with_context(self, grader_with_async_llm):
        """Test that answer with '不知道' as context (not conclusion) passes."""
        # LLM should recognize that '不知道' is context, not conclusion
        grader_with_async_llm.llm.acomplete.return_value = "HAS_ANSWER"
        answer = (
            "哥伦比娅诞生前听到的摇篮曲，实际上是由她自己唱的。"
            "她曾对旅行者提到'不知道是谁唱的'，是因为那时的她尚未找回这段记忆。"
        )
        result = await grader_with_async_llm._is_unknown_conclusion_async(
            "哥伦比娅诞生前听到的摇篮曲到底是谁唱的",
            answer
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_handles_llm_error(self, grader_with_async_llm):
        """Test graceful handling of LLM errors."""
        grader_with_async_llm.llm.acomplete.side_effect = Exception("API Error")
        result = await grader_with_async_llm._is_unknown_conclusion_async(
            "问题",
            "答案"
        )
        # Should default to False on error (don't block on errors)
        assert result is False
