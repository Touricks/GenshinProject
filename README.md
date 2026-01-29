# Genshin Story QA System (原神剧情问答系统)

> **Status**: Design Complete / Implementation Paused (Pending Review)
> **Latest Version**: PRD v1.2 | Tech Stack v1.2

## 1. 项目概览
本项目旨在构建一个基于 RAG (Retrieval-Augmented Generation) 的问答系统，专注于《原神》游戏剧情查询。系统利用 LLM (Gemini 3 Pro) 和向量数据库 (Qdrant) 提供高精度的剧情检索和问答能力。

## 2. 评测集设计 (Evaluation Strategy)

*摘录自 Setup Requirements，供评审参考*

### 评测目标
确保系统在回答事实性、关系型及多轮对话问题时的准确性与忠实度 (Faithfulness)。

### 数据集结构
计划构建 **~135 条** Golden Dataset，覆盖以下类别：

| 类别 | 数量 | 描述 | 对应 User Story |
|------|------|------|-----------------|
| **基础事实** | 50 | 角色身份、地点描述、单一事件 | US-1.1, US-1.2 |
| **关系查询** | 30 | 角色与组织的关系、人物互动 | US-2.1 |
| **跨章节追踪** | 20 | 跨越多个章节的事件脉络 | US-3.1 |
| **多轮对话** | 20 组 | 上下文理解、代词消解 (他/她/它) | US-4.1 |
| **边界测试** | 15 | 拒答无关问题、处理未知信息 | US-5.1 |

### 评测指标 (MVP 目标)
*   **Faithfulness (≥ 85%)**: 答案必须严格基于游戏文本，无幻觉。
*   **Context Recall (≥ 80%)**: 检索结果包含正确答案所需的上下文。
*   **Answer Relevancy (≥ 80%)**: 答案直接回应用户提问，不答非所问。

---
