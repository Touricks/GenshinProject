"""
Answer Grader for evaluating agent response quality.

This module provides a Hard Grader that uses an independent LLM call
to evaluate whether the agent's answer adequately addresses the user's question.
"""

import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# 硬性门槛配置
DEPTH_HARD_THRESHOLD = 10  # depth 分数必须 >= 10，否则直接不通过
SCORE_THRESHOLD = 70       # 总分阈值


GRADER_PROMPT = """你是一个答案质量评估器。请评估以下答案是否完整回答了用户问题。

## 用户问题
{question}

## Agent 答案
{answer}

## 工具调用记录
{tool_calls}

## 问题类型识别

首先判断问题类型：
- **关系类问题**: 如"X和Y是什么关系"、"X怎么认识Y"、"X和Y之间发生了什么"
- **事实类问题**: 如"X是谁"、"X的称号是什么"
- **历程类问题**: 如"X的经历"、"X是如何发展的"
- **细节类问题**: 如"X说了什么"、"描述某个场景"

## 评估标准

请根据以下5个维度评估，每个维度0-20分：

1. **工具调用验证** (0-20分)
   - 20分：调用了适当的工具验证实体/信息存在
   - 12分：调用了工具但不够全面
   - 5分：只调用了1次工具
   - 0分：没有调用任何工具

2. **证据支持** (0-20分)
   - 20分：答案完全基于工具返回的证据
   - 12分：大部分基于证据，少量推测
   - 5分：证据与答案关联弱
   - 0分：答案没有任何证据支持

3. **答案完整性** (0-20分)
   - 20分：完整回答了问题的所有方面
   - 12分：回答了主要方面，遗漏部分细节
   - 5分：只部分回答了问题
   - 0分：答案与问题无关或拒绝回答

4. **来源引用** (0-20分)
   - 20分：明确引用了 Chapter/Task ID 等来源
   - 12分：提到了来源但不具体
   - 5分：隐含引用但未明确
   - 0分：没有任何来源引用

5. **答案深度** (0-20分) - 特别重要！
   对于**关系类问题**：
   - 20分：描述了具体的互动事件、对话内容或关系发展过程
   - 12分：解释了关系的性质和背景
   - 5分：仅陈述存在某种关系类型（如"有互动关系"、"是朋友"）
   - 0分：答案无实质内容
   
## 特别注意

**关系类问题的深度检查**：
- 如果答案只说"X和Y有互动关系/是朋友/是敌人"而没有描述具体事件，答案深度必须≤5分
- 充分的关系描述应包含：具体发生了什么、在什么情境下、关系如何发展
- 只调用 find_connection 而没有调用 search_memory 的关系类回答，通常深度不足

## 输出格式

请严格返回以下JSON格式（不要添加任何其他文字）：

```json
{{
    "question_type": "<关系类/事实类/历程类/细节类>",
    "scores": {{
        "tool_usage": <0-20>,
        "evidence": <0-20>,
        "completeness": <0-20>,
        "citation": <0-20>,
        "depth": <0-20>
    }},
    "score": <0-100 总分>,
    "reason": "<简短理由，一句话>",
    "suggestion": "<如果未通过，给出具体改进建议>"
}}
```
"""


class AnswerGrader:
    """
    Hard Grader for evaluating agent answer quality.

    Uses an independent LLM call to score answers on 4 dimensions:
    1. Tool usage (did the agent verify with tools?)
    2. Evidence (is the answer based on tool results?)
    3. Completeness (does it fully answer the question?)
    4. Citation (are sources cited?)
    """

    def __init__(self, llm):
        """
        Initialize the grader.

        Args:
            llm: LlamaIndex LLM instance to use for grading.
        """
        self.llm = llm

    async def grade(
        self,
        question: str,
        answer: str,
        tool_calls: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Grade an answer for quality.

        Args:
            question: The original user question.
            answer: The agent's answer.
            tool_calls: List of tool calls made by the agent.

        Returns:
            Dict with keys: score (0-100), reason, suggestion, scores (breakdown)
        """
        # Format tool calls for the prompt
        if tool_calls:
            tool_calls_str = "\n".join([
                f"- {tc['tool']}({tc['kwargs']}) → {tc['output'][:200]}..."
                for tc in tool_calls
            ])
        else:
            tool_calls_str = "(没有调用任何工具)"

        # Build the grading prompt
        prompt = GRADER_PROMPT.format(
            question=question,
            answer=answer,
            tool_calls=tool_calls_str,
        )

        try:
            # Call LLM for grading
            response = await self.llm.acomplete(prompt)
            response_text = str(response)

            # Parse JSON from response
            # Try to extract JSON from the response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)

                # Validate required fields
                if "score" not in result:
                    result["score"] = sum(result.get("scores", {}).values())
                if "reason" not in result:
                    result["reason"] = "评估完成"
                if "suggestion" not in result:
                    result["suggestion"] = ""

                # 硬性门槛检查：depth < 10 直接不通过
                depth_score = result.get("scores", {}).get("depth", 0)
                total_score = result.get("score", 0)

                if depth_score < DEPTH_HARD_THRESHOLD:
                    result["passed"] = False
                    result["fail_reason"] = f"depth={depth_score} < {DEPTH_HARD_THRESHOLD} (硬性门槛)"
                    if not result.get("suggestion"):
                        result["suggestion"] = "答案深度不足，请调用 search_memory 获取具体剧情内容"
                    logger.info(f"Hard threshold failed: depth={depth_score}")
                elif total_score >= SCORE_THRESHOLD:
                    result["passed"] = True
                    result["fail_reason"] = None
                else:
                    result["passed"] = False
                    result["fail_reason"] = f"score={total_score} < {SCORE_THRESHOLD}"

                logger.debug(f"Grading result: {result}")
                return result
            else:
                logger.warning(f"Failed to parse grading JSON: {response_text[:200]}")
                return self._default_grade("无法解析评估结果")

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error in grading: {e}")
            return self._default_grade("JSON解析失败")
        except Exception as e:
            logger.error(f"Grading failed: {e}")
            return self._default_grade(f"评估失败: {str(e)}")

    def _default_grade(self, reason: str) -> Dict[str, Any]:
        """Return a default grade when grading fails."""
        return {
            "question_type": "未知",
            "scores": {
                "tool_usage": 0,
                "evidence": 0,
                "completeness": 0,
                "citation": 0,
                "depth": 0,
            },
            "score": 0,
            "passed": False,
            "fail_reason": reason,
            "reason": reason,
            "suggestion": "请重试或检查答案格式",
        }


def grade_sync(
    llm,
    question: str,
    answer: str,
    tool_calls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Synchronous grading function for testing.

    Args:
        llm: LlamaIndex LLM instance.
        question: The original user question.
        answer: The agent's answer.
        tool_calls: List of tool calls.

    Returns:
        Grading result dict.
    """
    import asyncio
    grader = AnswerGrader(llm)
    return asyncio.run(grader.grade(question, answer, tool_calls))
