# 1-Planning Phase

> Genshin Story QA System - 需求规划阶段

## 文档索引

| 文档 | 描述 | 状态 |
|------|------|------|
| [PRD.md](./PRD.md) | 产品需求文档 - 完整的产品定义 | Draft |
| [user-stories.md](./user-stories.md) | 用户故事 - 详细的功能描述和验收标准 | Draft |
| [risk-register.md](./risk-register.md) | 风险清单 - 已识别风险及缓解措施 | Active |

## 阶段目标

将模糊的需求转化为清晰、可执行的开发计划。

## 核心产出

- [x] PRD（产品需求文档）
- [x] 用户故事列表
- [x] 验收标准（Given-When-Then）
- [x] 风险清单
- [ ] 里程碑计划（见 [project_plan.md](../design/project_plan.md)）

## 关键决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 技术架构 | LlamaIndex + Mem0 | RAG + 记忆管理最佳组合 |
| 向量数据库 | Qdrant | 开源、自托管、性能优秀 |
| 嵌入模型 | BAAI/bge-base-zh-v1.5 | 中文语义嵌入 SOTA |
| LLM | Claude / GPT-4 | 强大的中文理解能力 |

## 版本范围

### MVP (v1.0)
- 基础向量检索问答
- 单轮对话
- 事实类查询
- 命令行接口

### v2.0
- 知识图谱集成
- 关系查询
- 跨章节追踪

### v3.0
- 多轮对话记忆
- Web UI
- 评测仪表盘

## 下一阶段

完成需求规划后，进入 [2-design](../../2-design/) 进行系统设计。

## 相关文档

- [技术选型报告](../design/techstack_report_claude.docx)
- [项目计划](../design/project_plan.md)
- [评测数据集](../evaluation/README.md)
