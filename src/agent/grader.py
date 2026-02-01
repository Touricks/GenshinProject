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
DEPTH_HARD_THRESHOLD = 15     # depth 分数必须 >= 15，否则直接不通过 (关系类问题需要调用 search_memory)
CITATION_HARD_THRESHOLD = 10   # citation 分数必须 >= 10，否则直接不通过 (按比例调整: 8/20*25=10)
SCORE_THRESHOLD = 70          # 总分阈值


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

请根据以下4个维度评估，每个维度0-25分：

1. **工具调用验证** (0-25分)
   - 25分：调用了多个适当的工具验证实体/信息
   - 18分：调用了适当的工具但不够全面
   - 10分：只调用了1次工具
   - 0分：没有调用任何工具

2. **答案完整性** (0-25分)
   - 25分：完整回答了问题的所有方面
   - 18分：回答了主要方面，遗漏部分细节
   - 10分：只部分回答了问题
   - 0分：答案与问题无关或拒绝回答

3. **来源引用** (0-25分)
   - 25分：明确引用了 Chapter/Task ID 等来源
   - 18分：提到了来源但不具体
   - 10分：隐含引用但未明确
   - 0分：没有任何来源引用

4. **答案深度** (0-25分) - 特别重要！

   **核心原则**: 深度分数取决于答案是否包含**具体证据**（对话原文、事件细节）

   **评分标准**:
   - 25分：引用了具体对话原文或事件细节
   - 18分：提到了关键信息点，但未直接引用原文
   - 10分：仅给出摘要性回答，无具体证据
   - 0分：答案过于笼统或纯属臆测

   **Few-Shot 示例**:

   示例1 - 低分 (depth=10):
   问题: "薇尔米娜为什么加入愚人众？"
   答案: "薇尔米娜加入愚人众是为了摆脱命运。"
   评分理由: 仅复述摘要，未引用具体对话，depth=10

   示例2 - 高分 (depth=25):
   问题: "薇尔米娜为什么加入愚人众？"
   答案: "根据第2章任务1601的对话，薇尔米娜的内心独白显示她的动机：'虚无的祈祷…还有今天加普依顽固的信仰…我只知道，这不是我要的生活…'。她发现旅行者打开了秘所后，决定'与其让它被外人偷走…不如，就让它成为我加入「愚人众」的敲门砖'。"
   评分理由: 引用了具体对话原文，解释了动机链，depth=25

## 特别注意

**不要验证引用内容**：
- Agent 可能使用了多轮对话的上下文信息，这些信息不一定出现在当前工具调用记录中
- 如果答案引用了具体的章节/任务ID，信任这些引用，不要因为"在工具输出中找不到"而扣分
- 只关注答案本身的质量（完整性、深度、是否有具体细节），不关注内容来源验证

**关系类问题的深度检查**：
- 如果答案只说"X和Y有互动关系/是朋友/是敌人"而没有描述具体事件，答案深度必须≤10分
- 充分的关系描述应包含：具体发生了什么、在什么情境下、关系如何发展
- 只调用 find_connection 而没有调用 search_memory 的关系类回答，通常深度不足

## 输出格式

请严格返回以下JSON格式（不要添加任何其他文字）：

```json
{{
    "question_type": "<关系类/事实类/历程类/细节类>",
    "scores": {{
        "tool_usage": <0-25>,
        "completeness": <0-25>,
        "citation": <0-25>,
        "depth": <0-25>
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
    2. Completeness (does it fully answer the question?)
    3. Citation (are sources cited?)
    4. Depth (does it include specific evidence?)
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
        # 增加截断长度到 2000 字符，确保完整 chunk 内容不被截断
        # 之前 800 字符导致关键证据（如角色死亡对话）被截断
        if tool_calls:
            tool_calls_str = "\n".join([
                f"- {tc['tool']}({tc['kwargs']}) → {tc['output'][:2000]}..."
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

                # 硬性门槛检查
                depth_score = result.get("scores", {}).get("depth", 0)
                citation_score = result.get("scores", {}).get("citation", 0)
                total_score = result.get("score", 0)

                # 按优先级检查各门槛
                if depth_score < DEPTH_HARD_THRESHOLD:
                    result["passed"] = False
                    result["fail_reason"] = f"depth={depth_score} < {DEPTH_HARD_THRESHOLD} (硬性门槛)"
                    if not result.get("suggestion"):
                        result["suggestion"] = "答案深度不足，请调用 search_memory 获取具体剧情内容"
                    logger.info(f"Hard threshold failed: depth={depth_score}")
                elif citation_score < CITATION_HARD_THRESHOLD:
                    result["passed"] = False
                    result["fail_reason"] = f"citation={citation_score} < {CITATION_HARD_THRESHOLD} (硬性门槛)"
                    if not result.get("suggestion"):
                        result["suggestion"] = "答案缺乏来源引用，请在回答中明确引用 Chapter/Task ID"
                    logger.info(f"Hard threshold failed: citation={citation_score}")
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
