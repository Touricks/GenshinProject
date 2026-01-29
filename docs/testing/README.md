# Testing Documentation

> 测试文档 | Testing & Evaluation Documents

本目录包含测试和评估相关的文档。

---

## 文档列表

| 文档 | 说明 |
|------|------|
| [evaluation-dataset.md](./evaluation-dataset.md) | 评估数据集设计 (Golden Dataset) |

---

## 评估指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| Recall@5 | ≥ 80% | 检索召回率 |
| Faithfulness | ≥ 85% | 答案忠实度 |
| P95 Latency | < 20s | 响应时间 |

---

## 数据集分类

| 数据集 | 数量 | 测试场景 |
|--------|------|----------|
| factual_qa | 50 条 | 基础事实查询 |
| relationship_qa | 30 条 | 关系查询 |
| tracking_qa | 20 条 | 跨章节追踪 |
| multiturn_qa | 15 条 | 多轮对话 |
| boundary_qa | 10 条 | 边界测试 |

---

## 评估框架

使用 [RAGAS](https://docs.ragas.io/) 进行自动化评估。
