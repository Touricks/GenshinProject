# ADR-001: 采用轻量级 DPO 优化 Plan 生成策略

> **状态**: Proposed
> **创建时间**: 2026-01-28T19:30:00+08:00
> **决策者**: Project Team
> **关联文档**: distill_plan.md, techstack-plan.md

---

## 1. 背景与问题 (Context)

### 1.1 当前架构设计

根据 `techstack-plan.md`，系统采用 **RAG-centric** 架构：

```
User Query → Retrieval (Qdrant/Neo4j) → LLM Generation → Answer
                    ↑
              知识存储在外部
              LLM 不"记忆"知识
```

### 1.2 引入的问题

在 `distill_plan.md v2.0` 中，我们提出了多智能体架构，包含 **Planner Agent** 负责生成检索计划。为提升 Planner 质量，初步计划使用：
- Phase 3: SFT (Supervised Fine-Tuning)
- Phase 4: DPO (Direct Preference Optimization)

### 1.3 核心矛盾

**风险**: 如果 DPO 训练数据包含 `Question → Answer` 对，模型可能：
1. 将知识"烤入"参数（Parametric Memory）
2. 绕过 RAG 直接生成答案
3. 丧失系统的可更新性和可解释性

**这与 PRD 的核心原则冲突**:
- 数据本地存储，不外传
- 依赖检索而非记忆
- 知识更新无需重新训练

---

## 2. 决策 (Decision)

**采用方案 B: 轻量级 DPO，仅优化 Plan 生成质量**

### 2.1 核心约束

```
DPO 训练范围:
  ✅ Plan 选择偏好 (哪种检索策略更好)
  ✅ 步骤排序偏好 (检索步骤的最优顺序)
  ❌ 知识问答对 (Question → Answer)
  ❌ 事实性内容 (任何原神剧情知识)
```

### 2.2 训练数据格式

```json
{
  "prompt": "【问题类型分析】\n用户问题: 恰斯卡和卡齐娜是什么关系？\n检测到实体: [恰斯卡, 卡齐娜]\n问题特征: 关系查询, 多实体\n\n请生成最优检索计划:",

  "chosen": {
    "strategy": "graph_augmented",
    "reasoning": "关系类问题需要图遍历找到实体间连接",
    "steps": [
      {"action": "extract_entities", "params": {}},
      {"action": "graph_traverse", "params": {"depth": 2}},
      {"action": "vector_search", "params": {"filter": "related_scenes"}},
      {"action": "aggregate", "params": {}}
    ]
  },

  "rejected": {
    "strategy": "vector_single_hop",
    "reasoning": "单跳检索无法捕获实体间关系",
    "steps": [
      {"action": "vector_search", "params": {"top_k": 10}}
    ]
  }
}
```

**关键点**:
- `chosen` 和 `rejected` 都是 **Plan**，不是 **Answer**
- 不包含任何原神剧情知识
- 模型学习的是「如何选择检索策略」

---

## 3. 备选方案 (Alternatives Considered)

### 方案 A: 去掉 DPO，纯 RAG + SFT

| 维度 | 评估 |
|------|------|
| RAG 纯粹性 | ✅ 最高，完全依赖外部检索 |
| Plan 质量 | ⚠️ 中等，SFT 可能不足以学好策略选择 |
| 开发成本 | ✅ 低 |
| 风险 | ✅ 低，无知识泄露风险 |

**未选择原因**: Planner Agent 的策略选择是核心能力，SFT 可能无法充分优化偏好。

### 方案 B: 轻量级 DPO（仅 Plan） ← 选定

| 维度 | 评估 |
|------|------|
| RAG 纯粹性 | ✅ 高，知识仍在外部 |
| Plan 质量 | ✅ 高，DPO 显式优化策略偏好 |
| 开发成本 | ⚠️ 中等，需构造偏好数据 |
| 风险 | ✅ 低，训练数据不含知识 |

**选择原因**: 在保持 RAG-centric 的同时，最大化 Planner 能力。

### 方案 C: 完整 DPO（含 Q→A）

| 维度 | 评估 |
|------|------|
| RAG 纯粹性 | ❌ 低，知识可能烤入模型 |
| Plan 质量 | ✅ 高 |
| 开发成本 | ⚠️ 中等 |
| 风险 | ❌ 高，与原始设计冲突 |

**未选择原因**: 违背 RAG-centric 原则，知识更新需重新训练。

### 方案 D: 无微调，纯 Prompt Engineering

| 维度 | 评估 |
|------|------|
| RAG 纯粹性 | ✅ 最高 |
| Plan 质量 | ⚠️ 依赖 Prompt 设计和基座模型能力 |
| 开发成本 | ✅ 最低 |
| 风险 | ✅ 最低 |

**未选择原因**: 基座模型（Gemini）可能无法稳定生成高质量 Plan，few-shot 示例有限。

---

## 4. 方案 B 详细设计

### 4.1 系统架构（不变）

```
┌─────────────────────────────────────────────────────────────┐
│                     用户界面 (Streamlit)                    │
├─────────────────────────────────────────────────────────────┤
│                      应用层                                  │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │  Planner Agent  │  │         Retriever Agent         │  │
│  │  (DPO 优化)     │  │    (无微调，调用外部存储)       │  │
│  │                 │  │                                 │  │
│  │  输入: Query    │  │  输入: Plan                     │  │
│  │  输出: Plan     │  │  输出: Retrieved Contexts       │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
│                              ↓                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Synthesizer (Gemini API)               │   │
│  │         基于检索结果生成答案，不依赖微调模型         │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                      存储层 (不变)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Qdrant    │  │   Neo4j     │  │    SQLite/Redis     │ │
│  │  (向量)     │  │  (图)       │  │   (会话/缓存)       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 各组件职责

| 组件 | 是否微调 | 职责 | 知识来源 |
|------|----------|------|----------|
| **Planner Agent** | ✅ SFT + DPO | 生成检索计划 | 无（只学策略） |
| **Retriever Agent** | ❌ 无微调 | 执行检索 | Qdrant, Neo4j |
| **Synthesizer** | ❌ 无微调 | 生成答案 | Retrieved Context |

**关键**: 知识始终存储在 Qdrant/Neo4j，LLM 只负责：
1. Planner: 选择检索策略
2. Synthesizer: 基于检索结果生成答案

### 4.3 Planner Agent 训练流程

```
Phase 1: SFT (格式学习)
├── 训练数据: Query → Plan (无偏好标注)
├── 目标: 学会生成格式正确的 Plan
└── 输出: Planner v0.1

Phase 2: DPO (偏好优化)
├── 训练数据: Query → (Chosen Plan, Rejected Plan)
├── 目标: 学会选择更优的检索策略
└── 输出: Planner v1.0
```

### 4.4 DPO 数据构造方法

```python
def generate_dpo_pair(query: str, query_type: str) -> dict:
    """
    为每个 query 生成 (chosen, rejected) Plan 对

    核心原则:
    - chosen/rejected 都是 Plan，不是 Answer
    - 不包含任何领域知识
    """

    # 策略优先级矩阵
    strategy_priority = {
        "factual": ["vector_single_hop", "graph_augmented"],      # 单跳优于图
        "relationship": ["graph_augmented", "vector_single_hop"],  # 图优于单跳
        "tracking": ["temporal_multi_hop", "vector_single_hop"],   # 时序优于单跳
        "multiturn": ["session_aware", "vector_single_hop"],       # 会话感知优于单跳
    }

    chosen_strategy = strategy_priority[query_type][0]
    rejected_strategy = strategy_priority[query_type][1]

    return {
        "prompt": f"问题: {query}\n类型: {query_type}\n生成检索计划:",
        "chosen": generate_plan(chosen_strategy),
        "rejected": generate_plan(rejected_strategy),
    }
```

---

## 5. 开发计划 (Development Plan)

### 5.1 时间线总览

```
Week 1-2: 基础设施 + MVP RAG
Week 3-4: Planner Agent SFT
Week 5:   DPO 数据构造
Week 6:   DPO 训练 + 评测
Week 7-8: 集成测试 + 优化
```

### 5.2 详细里程碑

| 阶段 | 时间戳 | 里程碑 | 交付物 | 验收标准 |
|------|--------|--------|--------|----------|
| **P1** | 2026-02-01 | MVP RAG | 单跳检索可用 | Factual QA 准确率 > 70% |
| **P1** | 2026-02-03 | Intent Classifier | 5类分类器 | 分类 F1 > 0.85 |
| **P1** | 2026-02-07 | Planner v0 (Rule-based) | 基于规则的 Plan 生成 | 能生成格式正确的 Plan |
| **P2** | 2026-02-10 | SFT 数据集 | 500+ (Query, Plan) 对 | 覆盖 5 类问题 |
| **P2** | 2026-02-14 | Planner v0.1 (SFT) | SFT 训练完成 | Plan 格式正确率 > 95% |
| **P3** | 2026-02-17 | DPO 数据集 | 300+ (Query, Chosen, Rejected) | 偏好标注一致性 > 90% |
| **P3** | 2026-02-21 | Planner v1.0 (DPO) | DPO 训练完成 | Plan 选择准确率 > 85% |
| **P4** | 2026-02-25 | 端到端集成 | 全流程打通 | 所有 QA 类型可运行 |
| **P4** | 2026-02-28 | RAGAS 评测 | 评测报告 | Faithfulness > 0.8 |
| **P5** | 2026-03-07 | 错误分析 | 改进计划 | 识别 Top-5 失败模式 |
| **P5** | 2026-03-10 | v1.0 Release | 最终版本 | 通过验收测试 |

### 5.3 资源分配

| 任务 | 计算资源 | 预估时间 |
|------|----------|----------|
| SFT 训练 (Planner) | M4 Pro MPS, 24GB | ~2-4 小时 |
| DPO 训练 (Planner) | M4 Pro MPS, 24GB | ~4-6 小时 |
| 推理服务 | Gemini API (免费额度) | - |
| 向量检索 | Qdrant (Docker) | - |

---

## 6. 优劣分析 (Pros & Cons)

### 6.1 优势 (Pros)

| # | 优势 | 说明 |
|---|------|------|
| 1 | **RAG 纯粹性保持** | 知识始终在外部存储，LLM 不记忆事实 |
| 2 | **可更新性** | 数据更新只需重新索引，无需重新训练 |
| 3 | **可解释性** | Plan 显式输出，用户可追溯检索过程 |
| 4 | **成本可控** | 只微调小型 Planner，不微调主 LLM |
| 5 | **风险隔离** | 即使 Planner 出错，Synthesizer 仍基于真实检索结果 |

### 6.2 劣势 (Cons)

| # | 劣势 | 缓解措施 |
|---|------|----------|
| 1 | **DPO 数据构造成本** | 使用规则 + Teacher 模型半自动生成 |
| 2 | **两阶段训练复杂度** | 先 SFT 验证格式，再 DPO 优化偏好，降低调试难度 |
| 3 | **Planner 错误传播** | 加入 Plan Validator，错误时 fallback 到默认策略 |
| 4 | **依赖 Intent 分类准确性** | Intent Classifier 与 Planner 解耦，可独立优化 |

### 6.3 与原始设计的对比

| 维度 | 原始 RAG 设计 | 方案 B (轻量 DPO) | 差异评估 |
|------|---------------|-------------------|----------|
| 知识存储位置 | 外部 (Qdrant/Neo4j) | 外部 (不变) | ✅ 一致 |
| LLM 角色 | 生成器 | 生成器 + Planner | ⚠️ 增加 Planner |
| 微调范围 | 无 | 仅 Planner (策略) | ⚠️ 新增微调 |
| 知识更新方式 | 重新索引 | 重新索引 (不变) | ✅ 一致 |
| 可解释性 | 中 | 高 (Plan 可见) | ✅ 提升 |

---

## 7. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| DPO 训练数据泄露知识 | 中 | 高 | 严格审核数据，禁止 Q→A 对 |
| Planner 过拟合特定问题模式 | 中 | 中 | 增加问题多样性，使用正则化 |
| Plan 执行失败无 fallback | 低 | 高 | 实现 default_strategy fallback |
| SFT 与 DPO 阶段不兼容 | 低 | 中 | 保持相同的 tokenizer 和格式 |

---

## 8. 决策结论

**采用方案 B: 轻量级 DPO**

理由：
1. 在保持 RAG-centric 架构的前提下，最大化 Planner 能力
2. 知识仍存储在外部，符合 PRD 核心原则
3. 训练成本可控，M4 Pro 本地可完成
4. Plan 显式输出，提升系统可解释性

---

## 9. 后续行动

- [ ] 2026-01-29: 定义 5 类问题的标准 Plan 模板
- [ ] 2026-01-30: 设计 SFT 数据生成 Pipeline
- [ ] 2026-02-01: 开始 MVP RAG 开发
- [ ] 2026-02-10: 完成 SFT 数据集构造

---

## 附录 A: 术语表

| 术语 | 定义 |
|------|------|
| **SFT** | Supervised Fine-Tuning，监督微调 |
| **DPO** | Direct Preference Optimization，直接偏好优化 |
| **RAG** | Retrieval-Augmented Generation，检索增强生成 |
| **Plan** | 检索计划，定义检索策略和步骤序列 |
| **Parametric Memory** | 参数化记忆，知识存储在模型参数中 |

## 附录 B: 参考文献

- [DPO Paper](https://arxiv.org/abs/2305.18290) - Direct Preference Optimization
- [RAG Survey](https://arxiv.org/abs/2312.10997) - Retrieval-Augmented Generation Survey
- [LlamaIndex Docs](https://docs.llamaindex.ai/) - RAG Framework
