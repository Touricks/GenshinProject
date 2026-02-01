"""Query Refiner for decomposing complex questions into targeted search queries.

This module provides the QueryRefiner class which takes a user question
and generates multiple search queries targeting different aspects of the question.
"""

import json
import logging
import re
from typing import List

logger = logging.getLogger(__name__)


REFINER_PROMPT = """你是一个查询分解专家。当向量搜索未能找到足够信息时，你需要将用户问题分解为多个针对性的搜索查询。

## 用户问题
{question}

## 上次搜索结果不足的原因
{suggestion}

## 任务
生成 2-3 个不同的搜索查询词，每个查询应该：
1. 针对问题的不同方面
2. 使用不同的关键词组合
3. 包含可能的别名或相关概念
4. 简洁精准，适合向量搜索

## 示例

问题: "努昂诺塔和少女是什么关系？"
输出: ["努昂诺塔 少女 相遇 见面", "努昂诺塔 创造 诞生 灵魂", "少女 月灵 起源"]

问题: "玛薇卡为什么要举办试炼？"
输出: ["玛薇卡 试炼 目的 原因", "纳塔 竞技场 传统", "火神 选拔 勇士"]

## 输出格式
只返回 JSON 数组，不要其他文字:
["查询1", "查询2", "查询3"]
"""


class QueryRefiner:
    """Decompose complex questions into multiple targeted search queries."""

    def __init__(self, llm=None):
        """
        Initialize QueryRefiner.

        Args:
            llm: Optional LlamaIndex LLM instance. If None, uses GRADER_MODEL
                 (a fast model like gemini-2.5-flash for speed priority).
        """
        if llm is not None:
            self.llm = llm
        else:
            # Use fast GRADER_MODEL by default
            from llama_index.llms.google_genai import GoogleGenAI
            from ..config import settings
            self.llm = GoogleGenAI(
                model=settings.GRADER_MODEL,
                is_function_calling_model=False,
            )

    async def refine(self, question: str, suggestion: str = "") -> List[str]:
        """
        Decompose a question into multiple search queries.

        Args:
            question: The original user question.
            suggestion: Feedback from grader about why previous search was insufficient.

        Returns:
            List of 2-3 targeted search queries.
        """
        prompt = REFINER_PROMPT.format(
            question=question,
            suggestion=suggestion or "需要更详细的信息",
        )

        try:
            response = await self.llm.acomplete(prompt)
            response_text = str(response).strip()

            # Extract JSON array from response
            # Handle cases where model might wrap it in markdown code blocks
            if "```" in response_text:
                match = re.search(r'\[.*?\]', response_text, re.DOTALL)
                if match:
                    response_text = match.group()

            queries = json.loads(response_text)

            if isinstance(queries, list) and len(queries) > 0:
                # Limit to 3 queries max
                queries = queries[:3]
                logger.info(f"Refined queries: {queries}")
                return queries
            else:
                logger.warning(f"Invalid refiner response format: {response_text}")
                return self._fallback_queries(question)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse refiner JSON: {e}")
            return self._fallback_queries(question)
        except Exception as e:
            logger.error(f"Refiner error: {e}")
            return self._fallback_queries(question)

    def _fallback_queries(self, question: str) -> List[str]:
        """
        Generate fallback queries when LLM fails.

        Simple heuristic: extract key terms from the question.
        """
        # Remove common question words
        stop_words = {"是", "什么", "为什么", "怎么", "如何", "的", "和", "与", "吗", "呢", "了"}
        words = [w for w in question if w not in stop_words and len(w) > 1]

        if len(words) >= 2:
            return [
                question,  # Original question
                " ".join(words[:3]),  # Key terms
            ]
        return [question]
