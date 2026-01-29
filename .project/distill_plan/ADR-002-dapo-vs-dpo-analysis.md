# ADR-002: DAPO vs DPO 技术选型分析

> **状态**: Proposed
> **创建时间**: 2026-01-28T20:00:00+08:00
> **前置文档**: ADR-001-lightweight-dpo.md
> **参考来源**: [DAPO Paper (arXiv)](https://arxiv.org/abs/2503.14476), [DPO Substack](https://cameronrwolfe.substack.com/p/direct-preference-optimization)

---

## 1. 背景

ADR-001 决定采用「轻量级 DPO」优化 Planner Agent。本文档评估是否应改用更新的 DAPO 算法。

---

## 2. DAPO vs DPO 核心差异

### 2.1 算法定位

| 维度 | DPO | DAPO |
|------|-----|------|
| **全称** | Direct Preference Optimization | Decoupled clip And dynamic sampling Policy Optimization |
| **提出者** | Stanford (2023) | ByteDance Seed (2025) |
| **设计目标** | 人类偏好对齐 | 长链推理 (Long-CoT) |
| **典型应用** | Chat 对齐、风格控制 | 数学推理 (AIME)、代码生成 |

### 2.2 技术机制对比

```
DPO (Offline, 静态偏好):
┌─────────────────────────────────────────────┐
│  训练数据: (prompt, chosen, rejected)       │
│  训练过程: 直接梯度下降，无 rollout         │
│  目标函数: max log(π(chosen)) - log(π(rejected)) │
└─────────────────────────────────────────────┘

DAPO (Online, 动态采样):
┌─────────────────────────────────────────────┐
│  训练数据: (prompt, verifiable_reward)      │
│  训练过程: 动态采样 + Policy Gradient       │
│  关键技术:                                  │
│    1. Clip-Higher: 防止熵崩溃               │
│    2. Dynamic Sampling: 在线生成样本        │
│    3. Token-Level Loss: 细粒度优化          │
│    4. Overlong Reward Shaping: 长序列处理   │
└─────────────────────────────────────────────┘
```

### 2.3 关键技术差异

| 技术点 | DPO | DAPO | 说明 |
|--------|-----|------|------|
| **采样方式** | 离线 (静态数据集) | 在线 (动态 rollout) | DAPO 需要推理时采样 |
| **奖励信号** | 隐式 (偏好对) | 显式 (可验证奖励) | DAPO 需要奖励函数 |
| **KL 约束** | 有 (reference model) | 无 | DAPO 更激进 |
| **Loss 粒度** | Sequence-level | Token-level | DAPO 更细粒度 |
| **计算成本** | 低 | 高 (需多次 forward) | DAPO ~3-5x 成本 |

### 2.4 适用场景

| 场景 | 推荐算法 | 原因 |
|------|----------|------|
| **Chat 对齐** | DPO | 静态偏好数据充足 |
| **风格/格式控制** | DPO | 无需复杂推理 |
| **数学推理** | DAPO | 答案可验证，需长 CoT |
| **代码生成** | DAPO | 可通过测试用例验证 |
| **检索策略选择** | **DPO** | 策略有限，偏好明确 |

---

## 3. 对 ADR-001 的影响分析

### 3.1 我们的任务特征

Planner Agent 的任务是：**根据问题类型选择最优检索策略**

```
输入: "恰斯卡和卡齐娜是什么关系？"
输出: Plan { strategy: "graph_augmented", steps: [...] }
```

**任务特征分析**:

| 特征 | 我们的任务 | DAPO 适用? | DPO 适用? |
|------|------------|------------|-----------|
| 输出空间 | 有限 (5种策略) | ❌ 过度 | ✅ 合适 |
| 可验证性 | 弱 (无标准答案) | ❌ 难以定义 reward | ✅ 偏好对足够 |
| 推理长度 | 短 (~50 tokens) | ❌ 非 Long-CoT | ✅ 合适 |
| 数据规模 | 小 (~300 对) | ❌ DAPO 需大量采样 | ✅ 足够 |

### 3.2 DAPO 的 Overkill 问题

DAPO 是为 **AIME 数学竞赛** 这类任务设计的：
- 答案可精确验证 (对/错)
- 需要长链推理 (数百 tokens)
- 探索空间巨大

我们的 Plan 生成任务：
- 只有 5 种策略，组合有限
- 输出简短，无需长链推理
- 偏好可以人工标注

**结论**: DAPO 引入的复杂性（动态采样、token-level loss）对我们的任务没有收益。

### 3.3 计算成本对比

| 资源 | DPO | DAPO | 我们的约束 |
|------|-----|------|------------|
| GPU 显存 | ~16GB | ~32GB+ | M4 Pro 24GB ⚠️ |
| 训练时间 | ~4h | ~12-20h | 有限 |
| 实现复杂度 | 低 (HF Trainer) | 高 (需自定义) | 偏好简单方案 |

---

## 4. 决策更新

### 4.1 结论

**维持 ADR-001 决策：使用 DPO，不采用 DAPO**

理由：
1. **任务复杂度不匹配**: Plan 生成是简单的分类/选择任务，非复杂推理
2. **奖励信号缺失**: 无法为 Plan 定义可验证的奖励函数
3. **计算资源受限**: M4 Pro 24GB 难以支撑 DAPO 的动态采样
4. **数据规模不足**: 300 对偏好数据不足以支撑 DAPO 的在线学习

### 4.2 可借鉴的 DAPO 思想

虽然不采用 DAPO 整体框架，但可借鉴部分思想：

| DAPO 技术 | 是否借鉴 | 应用方式 |
|-----------|----------|----------|
| **Clip-Higher** | ❌ | 不需要，策略空间小 |
| **Dynamic Sampling** | ❌ | 计算成本过高 |
| **Token-Level Loss** | ⚠️ 可选 | 若 Plan 格式不稳定可尝试 |
| **Overlong Shaping** | ❌ | Plan 输出短，不需要 |

### 4.3 未来演进路径

若后续需要更强的推理能力（如复杂的多跳规划），可考虑：

```
当前 (v1.0): DPO
  ↓ 若 Plan 质量不足
中期 (v2.0): GRPO (Group Relative Policy Optimization)
  ↓ 若需要复杂推理
远期 (v3.0): DAPO
```

---

## 5. 技术演进图谱

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM 偏好优化技术演进                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  RLHF (2022)                                                    │
│    ↓                                                            │
│  DPO (2023) ←── 我们选择这个                                    │
│    ↓                                                            │
│  IPO, KTO (2024)                                                │
│    ↓                                                            │
│  GRPO (DeepSeek, 2025)                                          │
│    ↓                                                            │
│  DAPO (ByteDance, 2025) ←── 为复杂推理设计，我们暂不需要        │
│    ↓                                                            │
│  GSPO, ... (未来)                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 风险评估更新

| 风险 | 原评估 (ADR-001) | 更新评估 |
|------|------------------|----------|
| DPO 效果不足 | 中 | 低 (任务简单，DPO 足够) |
| 需要升级到 DAPO | - | 低 (除非任务复杂度大幅增加) |
| 计算资源不足 | 低 | 低 (DPO 在 M4 Pro 可运行) |

---

## 7. 结论

| 问题 | 答案 |
|------|------|
| 是否需要用 DAPO 替代 DPO? | **否** |
| ADR-001 是否需要修改? | **否，维持原决策** |
| DAPO 何时考虑? | 若 Plan 复杂度大幅提升，或需要可验证奖励时 |

---

## 附录: 参考资料

- [DAPO: An Open-Source LLM Reinforcement Learning System at Scale](https://arxiv.org/abs/2503.14476)
- [Direct Preference Optimization (DPO) - Deep Learning Focus](https://cameronrwolfe.substack.com/p/direct-preference-optimization)
- [The State of Reinforcement Learning for LLM Reasoning](https://magazine.sebastianraschka.com/p/the-state-of-llm-reasoning-model-training)
- [It Takes Two: Your GRPO Is Secretly DPO](https://arxiv.org/html/2510.00977v1)
