# ADR-004: GRPO vs DPO 技术对比与选型决策

> **状态**: Proposed
> **创建时间**: 2026-01-28T21:00:00+08:00
> **前置文档**: ADR-001, ADR-002, ADR-003
> **参考来源**:
> - [GRPO Illustrated Breakdown](https://cameronrwolfe.substack.com/p/grpo)
> - [DeepSeek-R1 Paper](https://arxiv.org/abs/2501.12948)
> - [Why GRPO is Important](https://ghost.oxen.ai/why-grpo-is-important-and-how-it-works/)

---

## 1. 背景

DeepSeek-R1 的成功使 GRPO (Group Relative Policy Optimization) 成为 LLM 强化学习的热门选择。本文档对比 GRPO 与 DPO，评估哪种方法更适合我们的 Planner Agent。

---

## 2. 算法原理对比

### 2.1 DPO (Direct Preference Optimization)

```
核心思想: 将 RLHF 的奖励建模 + RL 训练合并为单一优化目标

输入: 静态偏好数据集 D = {(x, y_chosen, y_rejected)}
目标: 直接优化 policy 使其偏好 chosen 而非 rejected

Loss = -log σ(β · (log π(y_c|x)/π_ref(y_c|x) - log π(y_r|x)/π_ref(y_r|x)))

特点:
- 离线训练，无需在线采样
- 隐式奖励 (从偏好对中学习)
- 需要 reference model 做 KL 约束
```

### 2.2 GRPO (Group Relative Policy Optimization)

```
核心思想: 组内相对优势估计，无需 Value Network

流程:
1. 对每个 prompt x，采样一组响应 {y_1, ..., y_G}
2. 用 reward model 或规则对每个响应打分 r_i
3. 计算组内相对优势: A_i = (r_i - mean(r)) / std(r)
4. 用 Policy Gradient 更新: ∇L = -A_i · ∇log π(y_i|x)

特点:
- 在线训练，需要动态采样
- 显式奖励 (verifiable rewards)
- 无需 Critic/Value Network (vs PPO)
- 组内归一化提供稳定的优势估计
```

### 2.3 图解对比

```
┌─────────────────────────────────────────────────────────────────┐
│                         DPO 训练流程                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [静态数据集]                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │  Policy Model   │    │ Reference Model │                    │
│  │      π_θ        │    │     π_ref       │                    │
│  └────────┬────────┘    └────────┬────────┘                    │
│           │                      │                              │
│           └──────────┬───────────┘                              │
│                      ▼                                          │
│              Preference Loss                                    │
│        max log(π(chosen)/π(rejected))                          │
│                      │                                          │
│                      ▼                                          │
│               Gradient Update                                   │
│                                                                 │
│  内存需求: 2 个模型 (Policy + Reference)                        │
│  计算成本: 低 (无需采样)                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        GRPO 训练流程                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Prompt]                                                       │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐                                           │
│  │  Policy Model   │ ──────┐                                   │
│  │      π_θ        │       │ 采样 G 个响应                      │
│  └─────────────────┘       │                                   │
│                            ▼                                    │
│                   {y_1, y_2, ..., y_G}                         │
│                            │                                    │
│                            ▼                                    │
│                   ┌─────────────────┐                          │
│                   │  Reward Model   │  或 Rule-based Reward    │
│                   │   (可选)        │                          │
│                   └────────┬────────┘                          │
│                            │                                    │
│                            ▼                                    │
│                   {r_1, r_2, ..., r_G}                         │
│                            │                                    │
│                            ▼                                    │
│              Group Relative Advantage                           │
│              A_i = (r_i - mean) / std                          │
│                            │                                    │
│                            ▼                                    │
│              Policy Gradient Update                             │
│                                                                 │
│  内存需求: 1-2 个模型 (Policy + 可选 Reward Model)              │
│  计算成本: 高 (需要 G 次采样 + 评估)                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 维度对比表

| 维度 | DPO | GRPO | 备注 |
|------|-----|------|------|
| **训练范式** | 离线 (Offline) | 在线 (Online) | GRPO 需要动态采样 |
| **奖励信号** | 隐式 (偏好对) | 显式 (reward function) | GRPO 需要定义奖励 |
| **采样需求** | 无 | 每个 prompt 采样 G 次 | G 通常为 8-64 |
| **内存占用** | 2 模型 | 1-2 模型 | GRPO 无需 Reference |
| **计算成本** | 低 | 高 (~G 倍) | 采样是主要开销 |
| **KL 约束** | 有 (via reference) | 可选 (通常无) | GRPO 更激进 |
| **稳定性** | 高 | 中 (需要技巧) | GRPO 易出现熵崩溃 |
| **适用任务** | 偏好对齐、风格 | 推理、代码、数学 | 取决于是否有可验证奖励 |

---

## 4. 关键决策因素

### 4.1 是否能定义可验证奖励？

**GRPO 需要显式奖励函数**。对于我们的 Planner Agent：

| 奖励类型 | 能否定义 | 方法 |
|----------|----------|------|
| **Plan 格式正确性** | ✅ 可以 | 规则检查 JSON Schema |
| **策略选择准确性** | ⚠️ 部分可以 | 与 golden label 对比 |
| **检索效果 (最终)** | ✅ 可以 | 用 Sufficiency Evaluator 评估 |
| **端到端回答质量** | ⚠️ 困难 | 需要人工评估或 LLM-as-Judge |

**结论**: 可以为 Planner 定义部分可验证奖励，但不如数学题那样精确。

### 4.2 任务复杂度是否需要在线探索？

| 任务 | 输出空间 | 需要探索? | 推荐 |
|------|----------|-----------|------|
| 数学推理 (AIME) | 无限 (证明步骤) | ✅ 强烈需要 | GRPO |
| 代码生成 | 无限 (代码) | ✅ 需要 | GRPO |
| **Plan 生成** | **有限 (5种策略组合)** | **⚠️ 较弱** | **DPO 可能足够** |
| Chat 对齐 | 无限 (对话) | ❌ 不需要 | DPO |

**结论**: Plan 生成的输出空间有限，DPO 的离线学习可能足够。

### 4.3 计算资源约束

| 资源 | DPO | GRPO | 我们的约束 |
|------|-----|------|------------|
| GPU 显存 | ~16GB | ~24GB+ | M4 Pro 24GB ⚠️ |
| 训练时间 (300样本) | ~4h | ~12-20h | 有限 |
| 采样开销 | 无 | G=16 → 16x forward | 显著增加 |

**结论**: GRPO 对资源要求更高，但在我们的硬件上仍可运行。

---

## 5. 混合方案设计

考虑到两者的特点，提出 **渐进式方案**：

### 5.1 方案概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     渐进式训练策略                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: SFT (格式学习)                                        │
│      │    目标: 学会生成格式正确的 Plan                         │
│      │    数据: 500+ (Query, Plan) 对                           │
│      │                                                          │
│      ▼                                                          │
│  Phase 2: DPO (偏好学习)                                        │
│      │    目标: 学会选择更优的策略                              │
│      │    数据: 300+ (Query, Chosen, Rejected) 对               │
│      │                                                          │
│      ▼                                                          │
│  评估点: DPO 效果是否足够？                                     │
│      │                                                          │
│      ├──── 足够 ────▶ 完成，使用 DPO 模型                      │
│      │                                                          │
│      └──── 不足 ────▶ Phase 3: GRPO (强化探索)                 │
│                       目标: 通过在线采样发现更优策略            │
│                       奖励: 检索成功率 + 端到端质量             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 各阶段详细配置

#### Phase 1: SFT

```yaml
method: sft
data:
  format: alpaca
  samples: 500+
  source: Teacher 模型生成
objective: 格式正确率 > 95%
compute:
  device: M4 Pro MPS
  time: ~2h
```

#### Phase 2: DPO

```yaml
method: dpo
data:
  format: preference pairs
  samples: 300+
  source: 规则生成 + 人工验证
objective: 策略选择准确率 > 85%
compute:
  device: M4 Pro MPS
  time: ~4h
hyperparams:
  beta: 0.1  # KL 约束强度
  learning_rate: 5e-7
```

#### Phase 3: GRPO (可选)

```yaml
method: grpo
trigger: DPO 准确率 < 80% 或需要更强探索
data:
  prompts: 200+ 问题
  group_size: 16  # 每个问题采样 16 个 Plan
reward:
  - plan_format_valid: 0.1      # 格式正确
  - strategy_match_golden: 0.3  # 与标签匹配
  - retrieval_success: 0.3      # 检索成功
  - e2e_quality: 0.3            # 端到端质量 (LLM-as-Judge)
compute:
  device: M4 Pro MPS
  time: ~12-16h
hyperparams:
  clip_eps: 0.2
  no_kl: true  # GRPO 通常不用 KL
```

### 5.3 GRPO 奖励函数设计

```python
def compute_plan_reward(question: str, plan: Plan, golden_label: str) -> float:
    """
    为 Planner Agent 计算 GRPO 奖励

    奖励分解:
    - format_reward: Plan 格式是否正确 (0/1)
    - strategy_reward: 策略选择是否与 golden 匹配 (0/1)
    - retrieval_reward: 执行 Plan 后检索是否成功 (0/1)
    - e2e_reward: 端到端回答质量 (0-1, LLM-as-Judge)
    """

    # 1. 格式奖励 (规则)
    format_reward = 1.0 if validate_plan_schema(plan) else 0.0

    # 2. 策略奖励 (与标签对比)
    strategy_reward = 1.0 if plan.strategy in golden_label else 0.0

    # 3. 检索奖励 (执行并评估)
    contexts = execute_plan(plan, question)
    retrieval_reward = sufficiency_evaluator(question, contexts)

    # 4. 端到端奖励 (可选, LLM-as-Judge)
    if contexts:
        answer = synthesizer(question, contexts)
        e2e_reward = llm_judge(question, answer, golden_answer)
    else:
        e2e_reward = 0.0

    # 加权求和
    total_reward = (
        0.1 * format_reward +
        0.2 * strategy_reward +
        0.4 * retrieval_reward +
        0.3 * e2e_reward
    )

    return total_reward
```

---

## 6. 决策矩阵

| 场景 | 推荐方法 | 理由 |
|------|----------|------|
| **MVP 快速验证** | DPO | 实现简单，数据需求低 |
| **策略空间小，偏好明确** | DPO | 离线学习足够 |
| **需要发现新策略组合** | GRPO | 在线探索能力强 |
| **有精确奖励函数** | GRPO | 可充分利用奖励信号 |
| **计算资源受限** | DPO | 成本更低 |
| **追求最优性能** | DPO → GRPO | 渐进式提升 |

---

## 7. 最终建议

### 7.1 主推方案：DPO 优先，GRPO 备选

```
推荐路径:
  SFT → DPO → 评估 → (如需) GRPO

理由:
1. Plan 生成任务的输出空间有限，DPO 可能足够
2. DPO 实现简单，调试成本低
3. 如果 DPO 不足，可以平滑过渡到 GRPO
4. 保留 GRPO 作为性能提升手段
```

### 7.2 GRPO 触发条件

| 指标 | 阈值 | 触发 GRPO |
|------|------|-----------|
| DPO 策略准确率 | < 80% | ✅ |
| 多策略组合正确率 | < 70% | ✅ |
| 新问题泛化能力 | 下降 > 15% | ✅ |
| 用户反馈负面率 | > 20% | ✅ |

### 7.3 对 ADR 系列的总结

| ADR | 决策 | 状态 |
|-----|------|------|
| ADR-001 | 采用轻量级 DPO | ✅ 维持 |
| ADR-002 | DPO 优于 DAPO | ✅ 维持 |
| ADR-003 | 分层架构 + Sufficiency Evaluator | ✅ 维持 |
| **ADR-004** | **DPO 优先，GRPO 备选** | **新增** |

---

## 8. 实施时间线更新

| 阶段 | 时间 | 方法 | 交付物 |
|------|------|------|--------|
| P1 | Week 1-2 | - | MVP RAG |
| P2 | Week 3 | SFT | Planner v0.1 |
| P3 | Week 4 | DPO | Planner v1.0 |
| P4 | Week 5 | 评估 | DPO 效果报告 |
| P5 | Week 6 | GRPO (如需) | Planner v1.1 |
| P6 | Week 7-8 | 集成 | 最终系统 |

---

## 9. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| DPO 效果不足 | 中 | 中 | 保留 GRPO 升级路径 |
| GRPO 训练不稳定 | 中 | 高 | 使用 GRPO++ 技巧 (clip, entropy bonus) |
| 奖励函数设计不当 | 中 | 高 | 分解奖励，逐项调优 |
| 计算资源不足 | 低 | 中 | 减少 group_size，分批训练 |

---

## 10. 结论

| 问题 | 答案 |
|------|------|
| DPO vs GRPO 哪个更适合？ | **DPO 优先**，输出空间有限，离线学习足够 |
| 是否需要 GRPO？ | **视 DPO 效果而定**，作为备选升级路径 |
| 两者能否结合？ | **可以**，SFT → DPO → GRPO 渐进式训练 |

---

## 附录 A: GRPO 变体对比

| 变体 | 改进点 | 适用场景 |
|------|--------|----------|
| **Vanilla GRPO** | 基础版本 | 一般任务 |
| **GRPO++** | Clip + Entropy Bonus | 稳定性要求高 |
| **DR-GRPO** | 动态奖励缩放 | 奖励分布不均 |
| **DAPO** | 无 KL + Token-level | 复杂推理 |

## 附录 B: 参考资料

- [Group Relative Policy Optimization (GRPO)](https://cameronrwolfe.substack.com/p/grpo)
- [DeepSeek-R1 Paper](https://arxiv.org/abs/2501.12948)
- [Why GRPO is Important](https://ghost.oxen.ai/why-grpo-is-important-and-how-it-works/)
- [GRPO++ Tricks](https://cameronrwolfe.substack.com/p/grpo-tricks)
- [GRPO Illustrated Breakdown](https://epichka.com/blog/2025/grpo/)
