# ADR-003: 自适应检索与检索充分性判断

> **状态**: Revised (v2.0)
> **创建时间**: 2026-01-28T20:30:00+08:00
> **修订时间**: 2026-01-28T21:30:00+08:00
> **前置文档**: ADR-001, ADR-002
> **触发问题**:
> 1. 如果需要多种检索策略组合，DPO 能处理吗？
> 2. 检索后是否需要判断结果能否支持回答？
> 3. **[新增]** ReAct 模式如何进行 DPO？

---

## 1. 问题陈述

### 1.1 ADR-001 的隐含假设

```
假设: 每个问题只需要一种检索策略
流程: Question → Plan (单一策略) → Retrieve → Answer
```

### 1.2 实际场景反例

**场景 A: 需要策略组合**
```
问题: "恰斯卡和卡齐娜的关系在剧情中如何演变？"
需要:
  1. graph_augmented → 找到两人的关系类型
  2. temporal_multi_hop → 追踪关系在各章节的变化
```

**场景 B: 检索结果不足**
```
问题: "基尼奇第一次见到阿尤是什么情况？"
第一次检索: 只找到"基尼奇与阿尤并肩战斗"的片段
判断: 未回答"第一次见面"，需要补充检索
第二次检索: 扩大范围，找到初遇场景
```

**场景 C: 检索结果矛盾**
```
问题: "玛拉妮的师父是谁？"
检索结果 1: "玛拉妮跟随长老学习..."
检索结果 2: "玛拉妮是自学成才..."
判断: 信息矛盾，需要更多上下文或标注不确定性
```

### 1.3 核心缺失

| 缺失组件 | 影响 |
|----------|------|
| **策略组合器** | 无法处理需要多种策略的复杂问题 |
| **检索充分性评估器** | 无法判断何时停止检索 |
| **结果一致性检查器** | 无法处理矛盾信息 |
| **反馈循环** | 无法根据检索结果调整策略 |

---

## 2. 解决方案分析

### 2.1 方案 A: 扩展 DPO 为 Multi-Label

**思路**: 允许 DPO 输出策略集合而非单一策略

```json
{
  "prompt": "问题: 恰斯卡和卡齐娜关系如何演变？",
  "chosen": ["graph_augmented", "temporal_multi_hop"],
  "rejected": ["vector_single_hop"]
}
```

**问题**:
- DPO 设计为 pairwise comparison，不原生支持 multi-label
- 策略组合的执行顺序未定义
- 不解决检索充分性问题

**评估**: ⚠️ 部分解决问题 1，不解决问题 2

---

### 2.2 方案 B: ReAct 模式（迭代规划）

**思路**: 引入「思考-行动-观察」循环

```
┌─────────────────────────────────────────────────────────┐
│                    ReAct Loop                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Question                                               │
│      ↓                                                  │
│  [Thought] 分析问题，决定第一步策略                     │
│      ↓                                                  │
│  [Action] 执行检索 (graph_augmented)                    │
│      ↓                                                  │
│  [Observation] 检索结果: 找到关系类型，但无时间演变     │
│      ↓                                                  │
│  [Thought] 结果不足，需要补充时序信息                   │
│      ↓                                                  │
│  [Action] 执行检索 (temporal_multi_hop)                 │
│      ↓                                                  │
│  [Observation] 找到各章节的关系变化                     │
│      ↓                                                  │
│  [Thought] 信息充分，可以回答                           │
│      ↓                                                  │
│  [Answer] 综合两次检索结果生成答案                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**优点**:
- 自然支持多轮检索
- 显式的充分性判断（内置于 Thought）
- 可解释性强
- 灵活性最高（每步可根据观察调整）

**缺点**:
- ~~DPO 不直接适用~~ **[修订: 可通过特定方式应用 DPO]**
- 延迟增加（多轮 LLM 调用）
- 训练数据需要完整 trajectory

**评估**: ✅ 解决问题 1 和 2

#### 2.2.1 **[新增] ReAct + DPO 训练方法**

ReAct 可以通过以下方式应用 DPO：

##### 方法 1: Trajectory-level DPO（轨迹级 DPO）

```
比较完整的执行轨迹：
- chosen_trajectory: 高效完成任务的轨迹
- rejected_trajectory: 低效或失败的轨迹
```

```json
{
  "prompt": "问题: 恰斯卡和卡齐娜的关系如何演变？",

  "chosen": "[Thought] 这是关系+演变问题，需要先查关系再查时序\n[Action] graph_augmented\n[Obs] 找到朋友关系\n[Thought] 需要时序信息\n[Action] temporal_multi_hop\n[Obs] 找到演变过程\n[Thought] 信息充分\n[Answer] ...",

  "rejected": "[Thought] 直接搜索\n[Action] vector_single_hop\n[Obs] 只找到零散信息\n[Thought] 再搜一次\n[Action] vector_single_hop\n[Obs] 还是不够\n[Thought] 继续搜\n[Action] vector_single_hop\n..."
}
```

**优点**: 学习整体策略规划能力
**缺点**: 轨迹长，信用分配困难

##### 方法 2: Step-level DPO（步骤级 DPO）

```
在每个决策点比较不同的 Action 选择：
- 给定 (Question, History, Observation)
- chosen_action vs rejected_action
```

```json
{
  "prompt": "问题: 恰斯卡和卡齐娜的关系如何演变？\n[History]: 已执行 graph_augmented，找到关系类型\n[Observation]: 朋友关系，但无时间信息\n\n下一步 Action:",

  "chosen": "[Thought] 需要时序信息来追踪演变\n[Action] temporal_multi_hop",

  "rejected": "[Thought] 继续用同样方法\n[Action] vector_single_hop"
}
```

**优点**: 细粒度优化，信用分配明确
**缺点**: 需要标注每个决策点

##### 方法 3: Critical-step DPO（关键步骤 DPO）⭐ 推荐

```
只在关键决策点应用 DPO：
1. 首次策略选择
2. 是否继续检索的判断
3. 是否切换策略的判断
```

```json
// 关键决策 1: 首次策略选择
{
  "prompt": "问题: 恰斯卡和卡齐娜的关系如何演变？\n请选择首个检索策略:",
  "chosen": "graph_augmented (关系问题优先图检索)",
  "rejected": "vector_single_hop (单跳不足以处理关系)"
}

// 关键决策 2: 是否继续
{
  "prompt": "问题: ...?\n当前结果: 找到关系类型，但无演变信息\n是否继续检索?",
  "chosen": "继续，使用 temporal_multi_hop 补充时序",
  "rejected": "停止，当前信息足够 (错误判断)"
}

// 关键决策 3: 何时停止
{
  "prompt": "问题: ...?\n当前结果: 已有关系类型和时序演变\n是否继续检索?",
  "chosen": "停止，信息充分，可以回答",
  "rejected": "继续，再搜索更多细节 (过度检索)"
}
```

**优点**:
- 聚焦关键决策，数据效率高
- 避免过度检索和检索不足
- 与 DPO 的 pairwise 设计契合

**缺点**:
- 需要识别哪些是"关键步骤"

#### 2.2.2 ReAct + DPO 训练数据格式

```json
{
  "id": "react_dpo_001",
  "question": "恰斯卡和卡齐娜的关系如何演变？",
  "critical_steps": [
    {
      "step_type": "initial_strategy",
      "context": "问题分析：关系 + 时序演变",
      "chosen": {"thought": "关系问题需要图检索", "action": "graph_augmented"},
      "rejected": {"thought": "直接搜索", "action": "vector_single_hop"}
    },
    {
      "step_type": "continue_or_stop",
      "context": "已获取：关系类型=朋友",
      "observation": "找到关系但无演变信息",
      "chosen": {"thought": "需要补充时序", "action": "temporal_multi_hop"},
      "rejected": {"thought": "够了", "action": "stop"}
    },
    {
      "step_type": "continue_or_stop",
      "context": "已获取：关系类型 + 时序演变",
      "observation": "信息完整",
      "chosen": {"thought": "信息充分", "action": "stop"},
      "rejected": {"thought": "再多搜一些", "action": "vector_single_hop"}
    }
  ]
}
```

---

### 2.3 方案 C: 分层架构

**思路**: 分离「规划」和「评估」职责

```
┌─────────────────────────────────────────────────────────┐
│                  Hierarchical Architecture              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │            Meta-Planner (元规划器)              │   │
│  │  输入: Question                                 │   │
│  │  输出: 预定义策略序列 (一次性)                  │   │
│  │  训练: DPO (策略序列偏好)                       │   │
│  └─────────────────────────────────────────────────┘   │
│                          ↓                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │            Retriever (检索执行器)               │   │
│  │  按 Meta-Planner 的计划依次执行检索             │   │
│  │  无需训练                                       │   │
│  └─────────────────────────────────────────────────┘   │
│                          ↓                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │         Sufficiency Evaluator (充分性评估器)    │   │
│  │  输入: Question + Retrieved Contexts            │   │
│  │  输出: Sufficient / Insufficient + Reason       │   │
│  │  训练: Binary Classification (SFT)              │   │
│  └─────────────────────────────────────────────────┘   │
│                          ↓                              │
│              ┌──────────┴──────────┐                   │
│              ↓                     ↓                    │
│         Sufficient            Insufficient              │
│              ↓                     ↓                    │
│         Synthesizer         Fallback Strategy           │
│         生成答案            (扩大检索/标注不确定)       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**与方案 B 的关键区别**:

| 维度 | 方案 B (ReAct) | 方案 C (分层) |
|------|----------------|---------------|
| **决策时机** | 每步动态决策 | 预先规划 + 事后评估 |
| **反馈粒度** | 细粒度 (每步 Thought) | 粗粒度 (整个计划) |
| **模型数量** | 1 个统一模型 | 多个专用组件 |
| **灵活性** | 高（可随时调整） | 中（计划固定） |
| **可独立测试** | 低 | 高 |

**评估**: ✅ 解决问题 1 和 2，但灵活性低于方案 B

---

### 2.4 方案 D: Self-RAG 模式

**思路**: 引入 Critic 模型评估检索质量

```
Self-RAG 特殊 Token:
  [Retrieve]: 是否需要检索
  [IsRel]: 检索结果是否相关
  [IsSup]: 检索结果是否支持回答
  [IsUse]: 生成的答案是否有用
```

**优点**:
- 学术界验证有效
- 端到端训练

**缺点**:
- 需要预训练特殊 token
- 实现复杂度高
- 对基座模型有要求

**评估**: ⚠️ 有效但实现成本高

---

## 3. 方案对比矩阵 (修订版)

| 维度 | 方案 A | 方案 B (ReAct) | 方案 C (分层) | 方案 D |
|------|--------|----------------|---------------|--------|
| 解决多策略组合 | ⚠️ | ✅ | ✅ | ✅ |
| 解决充分性判断 | ❌ | ✅ (内置) | ✅ (独立组件) | ✅ |
| 动态调整能力 | ❌ | ✅ 强 | ⚠️ 弱 | ✅ |
| 实现复杂度 | 低 | 中 | 中 | 高 |
| 可独立测试 | ❌ | ❌ | ✅ | ❌ |
| **DPO 兼容性** | ⚠️ | **✅ (Critical-step)** | ✅ | ❌ |
| 训练数据需求 | 低 | 中 | 低 | 高 |

---

## 4. 决策修订：方案 B (ReAct + Critical-step DPO) 为主，方案 C 为备选

### 4.1 修订理由

原决策选择方案 C，主要考虑「DPO 兼容性」。但经分析，**ReAct 可以通过 Critical-step DPO 进行训练**，同时保留更强的动态调整能力。

| 原顾虑 | 解决方案 |
|--------|----------|
| ReAct 无法用 DPO | Critical-step DPO 可行 |
| 训练数据复杂 | 只标注关键决策点 |
| 延迟增加 | 可接受，换取灵活性 |

### 4.2 新架构：ReAct + Critical-step DPO

```
┌─────────────────────────────────────────────────────────────┐
│                  ReAct Agent Architecture (v3.0)            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User Query                                                 │
│      │                                                      │
│      ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ReAct Agent (统一模型)                  │   │
│  │                                                     │   │
│  │   训练方法:                                         │   │
│  │   - Phase 1: SFT (学习 ReAct 格式)                  │   │
│  │   - Phase 2: Critical-step DPO (优化关键决策)       │   │
│  │                                                     │   │
│  │   ┌─────────────────────────────────────────────┐  │   │
│  │   │              ReAct Loop                      │  │   │
│  │   │                                             │  │   │
│  │   │  [Thought] 分析问题 ─────────────────────┐  │  │   │
│  │   │      │                                   │  │  │   │
│  │   │      ▼                     DPO 优化点 ◄──┘  │  │   │
│  │   │  [Action] 选择策略 ─────────────────────┐  │  │   │
│  │   │      │                                   │  │  │   │
│  │   │      ▼                     DPO 优化点 ◄──┘  │  │   │
│  │   │  [Observation] 检索结果                  │  │   │
│  │   │      │                                   │  │   │
│  │   │      ▼                                   │  │   │
│  │   │  [Thought] 评估充分性 ──────────────────┐  │  │   │
│  │   │      │                                   │  │  │   │
│  │   │      ├─ 不足 ──▶ 继续循环    DPO 优化点 ◄──┘  │   │
│  │   │      │                                      │   │
│  │   │      └─ 充分 ──▶ [Answer] 生成答案          │   │
│  │   │                                             │   │
│  │   └─────────────────────────────────────────────┘  │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  外部工具:                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Qdrant    │  │   Neo4j     │  │    Synthesizer      │ │
│  │  (向量)     │  │  (图)       │  │   (Gemini API)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Critical-step DPO 训练细节

#### DPO 优化的 3 个关键决策点

| 决策点 | 触发条件 | DPO 目标 |
|--------|----------|----------|
| **D1: 首次策略选择** | 收到问题后 | 选择最合适的首个策略 |
| **D2: 继续/停止** | 每次 Observation 后 | 判断是否需要继续检索 |
| **D3: 策略切换** | 当前策略效果不佳时 | 选择更合适的替代策略 |

#### 训练数据格式

```json
{
  "id": "react_critical_dpo_001",
  "question": "恰斯卡和卡齐娜的关系如何演变？",
  "dpo_pairs": [
    {
      "decision_point": "D1_initial_strategy",
      "prompt": "问题: 恰斯卡和卡齐娜的关系如何演变？\n\n[Thought] 这是一个关于角色关系及其时间演变的问题。\n\n请选择 Action:",
      "chosen": "[Action] graph_augmented\n[Reason] 关系问题需要图结构来找到实体间连接",
      "rejected": "[Action] vector_single_hop\n[Reason] 直接搜索可能找到相关内容"
    },
    {
      "decision_point": "D2_continue_or_stop",
      "prompt": "问题: 恰斯卡和卡齐娜的关系如何演变？\n\n[History]\n- Action: graph_augmented\n- Result: 找到她们是朋友/战友关系\n\n[Observation] 获得关系类型，但无时间演变信息\n\n[Thought] 评估当前信息是否充分:",
      "chosen": "[Decision] 继续检索\n[Action] temporal_multi_hop\n[Reason] 需要补充时序信息以回答"如何演变"",
      "rejected": "[Decision] 停止检索\n[Action] answer\n[Reason] 已有足够信息 (错误：缺少演变部分)"
    },
    {
      "decision_point": "D2_continue_or_stop",
      "prompt": "问题: 恰斯卡和卡齐娜的关系如何演变？\n\n[History]\n- Action 1: graph_augmented → 朋友/战友\n- Action 2: temporal_multi_hop → 从初识到并肩作战的演变过程\n\n[Observation] 已获取关系类型和时间演变\n\n[Thought] 评估当前信息是否充分:",
      "chosen": "[Decision] 停止检索\n[Action] answer\n[Reason] 信息充分，可以完整回答问题",
      "rejected": "[Decision] 继续检索\n[Action] vector_single_hop\n[Reason] 再搜索更多细节 (错误：过度检索)"
    }
  ]
}
```

### 4.4 训练流程

```
┌─────────────────────────────────────────────────────────────┐
│                    训练流程 (ReAct + DPO)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: SFT (格式学习)                                    │
│  ├── 数据: 完整 ReAct trajectory (无偏好标注)               │
│  ├── 目标: 学会 [Thought][Action][Observation] 格式         │
│  ├── 样本量: ~300 trajectories                              │
│  └── 输出: ReAct Agent v0.1                                 │
│                                                             │
│  Phase 2: Critical-step DPO (关键决策优化)                  │
│  ├── 数据: 关键决策点的 (chosen, rejected) 对               │
│  ├── 目标: 优化策略选择和停止判断                           │
│  ├── 样本量: ~500 decision pairs (从 ~150 问题中提取)       │
│  └── 输出: ReAct Agent v1.0                                 │
│                                                             │
│  Phase 3: (可选) GRPO 强化                                  │
│  ├── 触发: 若 DPO 效果不足                                  │
│  ├── 奖励: 检索效率 + 答案质量                              │
│  └── 输出: ReAct Agent v1.1                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 方案 C 作为备选

若 ReAct + DPO 实现复杂度过高，可退回方案 C：

| 场景 | 选择 |
|------|------|
| 默认推荐 | 方案 B (ReAct + Critical-step DPO) |
| 实现复杂度约束 | 方案 C (分层架构) |
| 快速 MVP | 方案 C (组件可独立开发) |

方案 C 的优势是**可独立测试**：
- Meta-Planner 可单独评测策略选择准确率
- Sufficiency Evaluator 可单独评测判断准确率

---

## 6. 实施计划更新

### 6.1 主方案 (ReAct + DPO)

| 阶段 | 时间戳 | 里程碑 | 交付物 |
|------|--------|--------|--------|
| P1 | 2026-02-07 | ReAct 格式定义 | Prompt Template |
| P2 | 2026-02-14 | ReAct SFT | Agent v0.1 |
| P3 | 2026-02-21 | Critical-step DPO 数据 | 500+ pairs |
| P4 | 2026-02-25 | Critical-step DPO 训练 | Agent v1.0 |
| P5 | 2026-02-28 | 端到端评测 | RAGAS 报告 |

### 6.2 备选方案 (分层架构)

若 P2 后评估 ReAct 复杂度过高，切换到方案 C：

| 阶段 | 时间戳 | 里程碑 | 交付物 |
|------|--------|--------|--------|
| P2-alt | 2026-02-14 | Meta-Planner SFT | Planner v0.1 |
| P3-alt | 2026-02-17 | Sufficiency Evaluator | Evaluator v0.1 |
| P4-alt | 2026-02-21 | Meta-Planner DPO | Planner v1.0 |

---

## 7. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| ReAct 训练不稳定 | 中 | 高 | 退回方案 C |
| Critical-step 标注成本高 | 中 | 中 | 半自动生成 + 人工验证 |
| 多轮延迟影响体验 | 中 | 中 | 设置 max_turns=5 |
| DPO 未能学会停止判断 | 中 | 高 | 增加停止判断的训练数据比例 |

---

## 8. 结论 (修订版)

### 8.1 关键修订

| 原决策 | 修订后 |
|--------|--------|
| 方案 C (分层架构) | **方案 B (ReAct + Critical-step DPO)** |
| DPO 不适用于 ReAct | **Critical-step DPO 可行** |
| Sufficiency Evaluator 独立组件 | **内置于 ReAct Thought** |

### 8.2 最终架构选择

**主推**: ReAct + Critical-step DPO
- 统一模型处理规划、执行、评估
- 细粒度动态调整能力
- DPO 优化关键决策点

**备选**: 分层架构 (方案 C)
- 若 ReAct 实现复杂度过高
- 组件可独立开发测试

### 8.3 DPO 在 ReAct 中的应用总结

```
ReAct + DPO 训练策略:

1. SFT 阶段: 学习 ReAct 格式和基本行为
   - 输入: 完整 trajectory
   - 输出: 格式正确的 Agent

2. DPO 阶段: 优化关键决策
   - D1: 首次策略选择 (选什么)
   - D2: 继续/停止判断 (够不够)
   - D3: 策略切换 (换不换)

关键: 不需要对整个 trajectory 做 DPO，
     只需要在关键决策点应用 pairwise comparison
```

---

## 附录 A: ReAct Prompt Template

```
你是一个原神剧情检索专家。使用 ReAct 模式回答问题。

格式:
[Thought] 你的分析和推理
[Action] 选择一个动作: graph_augmented | temporal_multi_hop | vector_single_hop | session_aware | answer
[Observation] (系统返回的检索结果)

规则:
1. 每次只执行一个 Action
2. 根据 Observation 决定下一步
3. 当信息充分时，选择 [Action] answer 并给出最终答案
4. 最多执行 5 轮检索

问题: {question}

开始:
[Thought]
```

## 附录 B: 检索充分性判断标准 (内置于 Thought)

| 充分性级别 | Thought 模式 | 下一步 Action |
|------------|--------------|---------------|
| **Fully Sufficient** | "信息完整，可以回答" | answer |
| **Partially Sufficient** | "缺少 X 方面信息" | 补充检索 |
| **Contradictory** | "信息存在矛盾" | 扩大检索或标注不确定 |
| **Insufficient** | "当前结果不相关" | 换策略 |
| **Max Turns Reached** | "已达最大轮次" | answer (标注信息可能不完整) |
