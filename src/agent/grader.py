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
DEPTH_HARD_THRESHOLD = 8      # depth 分数必须 >= 8，否则直接不通过
CITATION_HARD_THRESHOLD = 0   # 禁用 citation 门槛（Agent 不会自动添加引用）
EVIDENCE_HARD_THRESHOLD = 5   # evidence 分数必须 >= 5，配合放宽的 prompt
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

请根据以下5个维度评估，每个维度0-20分：

1. **工具调用验证** (0-20分)
   - 20分：调用了适当的工具验证实体/信息存在
   - 12分：调用了工具但不够全面
   - 5分：只调用了1次工具
   - 0分：没有调用任何工具

2. **证据支持** (0-20分) - 语义验证而非逐字匹配

   **验证步骤**：
   a. 从答案中提取所有关键声明（如"X发生了Y"、"A拥有B"）
   b. 对每个声明，检查是否与 tool output 矛盾
   c. 只有与 tool output 直接矛盾的内容才是幻觉

   **评分**：
   - 20分：所有关键声明都能在 tool output 中找到明确支持，或不矛盾
   - 15分：大部分声明有支持，少量无法验证但不矛盾
   - 10分：核心声明有支持，存在一些无法验证的细节（可能因截断）
   - 5分：只有部分声明有支持，但无明显矛盾
   - 0分：主要声明与 tool output 直接矛盾（真正的幻觉）

   **重要澄清**：
   - 如果 tool output 提到了某个实体/事件，答案对其进行总结或重新表述不是幻觉
   - 从多个 tool output 综合推理出的结论不是幻觉
   - 专有名词的别名/全名使用不是幻觉（如"少女"和"露珠"可能指同一角色）
   - 无法在截断后的 tool output 中验证、但也不矛盾的内容，应给予合理怀疑的空间
   - 只有与 tool output 直接矛盾的内容才是幻觉

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

   **核心原则**: 深度分数取决于是否引用了 tool output 中的**具体证据**（对话原文、事件细节）

   **评分标准**:
   - 20分：引用了 tool output 中的具体对话原文或事件细节
   - 12分：提到了 tool output 中的关键信息点，但未直接引用原文
   - 5分：仅复述 tool output 的摘要/标题，无具体证据
   - 0分：答案与 tool output 无关或纯属臆测

   **Few-Shot 示例**:

   示例1 - 低分 (depth=5):
   问题: "薇尔米娜为什么加入愚人众？"
   Tool output 包含: "薇尔米娜：（与其让它被外人偷走…不如，就让它成为我加入「愚人众」的敲门砖…）"
   答案: "薇尔米娜加入愚人众是为了摆脱命运。"
   评分理由: 仅复述摘要，未引用具体对话，depth=5

   示例2 - 高分 (depth=20):
   问题: "薇尔米娜为什么加入愚人众？"
   Tool output 同上
   答案: "根据第2章任务1601的对话，薇尔米娜的内心独白显示她的动机：'虚无的祈祷…还有今天加普依顽固的信仰…我只知道，这不是我要的生活…'。她发现旅行者打开了秘所后，决定'与其让它被外人偷走…不如，就让它成为我加入「愚人众」的敲门砖'。"
   评分理由: 引用了具体对话原文，解释了动机链，depth=20

## 特别注意

**工具输出截断说明**：
- 为控制 prompt 长度，tool output 可能只显示前 2000 字符
- 因此在评估时要考虑：完整输出可能包含更多证据
- 如果答案与显示的 tool output 不矛盾，即使找不到精确支持也不应轻易判定为幻觉

**幻觉检测（严格定义）**：
- 幻觉是指：与 tool output 直接矛盾的内容
- 以下情况不是幻觉：
  - 对 tool output 内容的总结、归纳、重新表述
  - 从多个 tool output 综合推理出的结论
  - 使用实体的别名/全名（如"少女"="露珠"）
  - 基于 tool output 的合理推断（如 A→B 且 B→C，则推断 A→C）
  - 无法在截断后的 tool output 中验证、但也不矛盾的内容
- 只有当答案与 tool output 直接矛盾时才标记为幻觉

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
    "suggestion": "<如果未通过，给出具体改进建议>",
    "hallucination_detected": "<如果发现答案中有 tool output 不支持的内容，列出这些内容>"
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
                evidence_score = result.get("scores", {}).get("evidence", 0)
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
                elif evidence_score < EVIDENCE_HARD_THRESHOLD:
                    result["passed"] = False
                    result["fail_reason"] = f"evidence={evidence_score} < {EVIDENCE_HARD_THRESHOLD} (硬性门槛)"
                    if not result.get("suggestion"):
                        result["suggestion"] = "答案证据支持不足，请确保回答基于工具返回的实际内容"
                    logger.info(f"Hard threshold failed: evidence={evidence_score}")
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
