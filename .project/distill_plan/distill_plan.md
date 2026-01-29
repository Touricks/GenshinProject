# 数据蒸馏与多智能体训练方案 (Data Distillation & Multi-Agent Training Plan)

> **版本**: 2.0
> **更新时间**: 2026-01-28T18:55:00+08:00
> **状态**: Design Draft

---

## 1. 核心问题重述

### 1.1 原问题 (v1.0)
> "蒸馏原始输入会改变 Agent 的输入格式。这对 Agent（而非 Model）可行吗？"

**结论**: 如果只做简单的 Q→A 训练，对于 Model（知识库）可行，但对于 Agent（工具使用者/阅读者）不足。

### 1.2 新问题 (v2.0)
> "对于需要从多处获取数据的问题，纯 GraphRAG 不够，需要 'specific plan' 来管理记忆。如何设计？"

**核心洞察**: 不同问题类型需要不同的**检索计划 (Retrieval Plan)**。我们需要一个多智能体架构，其中 **Planner Agent** 负责：
1. 问题分类与意图识别
2. 生成检索计划（哪些数据源、什么顺序）
3. 协调执行子 Agent
4. 聚合与合成结果

---

## 2. 多智能体架构设计

### 2.1 架构总览

```
                          ┌─────────────────────────────────┐
                          │         Orchestrator            │
                          │   (主控 Agent / Query Router)   │
                          └───────────────┬─────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
              ▼                           ▼                           ▼
   ┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
   │  Planner Agent   │       │  Retriever Agent │       │  Synthesizer     │
   │  (计划生成器)    │       │  (检索执行器)    │       │  Agent (合成器)  │
   └────────┬─────────┘       └────────┬─────────┘       └──────────────────┘
            │                          │
            │   Plan                   │   Execute
            ▼                          ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                        Retrieval Strategies                          │
   │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐ │
   │  │ Vector     │  │ Graph      │  │ Temporal   │  │ Session        │ │
   │  │ (单跳事实) │  │ (关系查询) │  │ (跨章追踪) │  │ (多轮记忆)     │ │
   │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘ │
   └──────────────────────────────────────────────────────────────────────┘
```

### 2.2 各问题类型的处理策略

| 问题类型 | 示例 | 检索策略 | 记忆管理 |
|----------|------|----------|----------|
| **Factual QA** | "玛拉妮的性格?" | Vector Search (单跳) | 无需跨 context |
| **Relationship QA** | "恰斯卡和卡齐娜的关系?" | Graph Traversal + Vector | 图结构缓存 |
| **Tracking QA** | "旅行者如何获得古名?" | Multi-hop Temporal | Timeline Memory |
| **Multi-turn QA** | "上一轮说的'他'是谁?" | Session Memory + CoRef | Sliding Window + Entity Cache |
| **Boundary QA** | "钢铁侠能打赢火神吗?" | Intent Classification | 拒绝逻辑 |

### 2.3 Planner Agent 的计划生成逻辑

```python
# Pseudo-code for Planner Agent
def generate_retrieval_plan(question: str, session_context: SessionContext) -> Plan:
    # Step 1: 意图分类
    intent = classify_intent(question)  # factual|relationship|tracking|multiturn|boundary

    # Step 2: 根据意图生成计划
    if intent == "factual":
        return Plan(
            strategy="vector_single_hop",
            data_sources=["qdrant:genshin_story"],
            steps=[
                Step("embed_query", {}),
                Step("vector_search", {"top_k": 10}),
                Step("rerank", {"top_k": 5}),
            ]
        )

    elif intent == "relationship":
        return Plan(
            strategy="graph_augmented",
            data_sources=["neo4j:characters", "qdrant:genshin_story"],
            steps=[
                Step("extract_entities", {}),
                Step("graph_traverse", {"depth": 2, "relation_types": ["friend_of", "enemy_of"]}),
                Step("vector_search", {"filter": "related_scenes", "top_k": 10}),
                Step("aggregate_multi_source", {}),
            ]
        )

    elif intent == "tracking":
        return Plan(
            strategy="temporal_multi_hop",
            data_sources=["qdrant:genshin_story"],
            steps=[
                Step("decompose_to_milestones", {}),  # 分解为时间线里程碑
                Step("sequential_retrieval", {"milestones": "auto"}),
                Step("temporal_ordering", {}),
                Step("synthesize_timeline", {}),
            ]
        )

    elif intent == "multiturn":
        return Plan(
            strategy="session_aware",
            data_sources=["session_memory", "qdrant:genshin_story"],
            steps=[
                Step("resolve_coreference", {"session": session_context}),
                Step("rewrite_query", {}),
                Step("vector_search", {"top_k": 10}),
            ]
        )

    else:  # boundary
        return Plan(
            strategy="guard",
            steps=[Step("refuse_with_reason", {"reason": "out_of_scope"})]
        )
```

---

## 3. 记忆管理策略 (Memory Management)

### 3.1 问题：为什么 GraphRAG 不够？

GraphRAG 的局限性：
1. **静态图结构**：预构建的图无法适应动态问题
2. **单一检索路径**：不支持"先图后向量"或"先向量后图"的混合策略
3. **无时序感知**：难以处理"事件演变"类问题

### 3.2 解决方案：Plan-Based Memory

不依赖单一的 GraphRAG，而是让 Planner Agent 根据问题**动态生成检索计划**，并维护**执行时记忆 (Execution Memory)**：

```
┌─────────────────────────────────────────────────────────────┐
│                    Execution Memory                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Working Memory  │  │ Intermediate    │                  │
│  │ (当前步骤上下文)│  │ Results Cache   │                  │
│  │                 │  │ (子查询结果)    │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Plan Execution State                    │   │
│  │  current_step: 2/4                                   │   │
│  │  completed: [entity_extraction, graph_traverse]      │   │
│  │  pending: [vector_search, synthesis]                 │   │
│  │  collected_contexts: [{scene_1}, {scene_2}]          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 三层记忆架构

| 层级 | 名称 | 生命周期 | 用途 |
|------|------|----------|------|
| L1 | **Working Memory** | 单次查询 | 当前检索步骤的上下文 |
| L2 | **Session Memory** | 会话级 | 多轮对话历史、指代消解 |
| L3 | **Long-term Memory** | 持久化 | 用户偏好、常用实体 (Mem0 v3.0) |

---

## 4. 蒸馏训练数据设计 (Distillation Dataset)

### 4.1 设计原则 (v2.0 更新)

**核心变化**: 不仅蒸馏 Q→A，还要蒸馏 **Q→Plan→Execution→A**。

```
v1.0:  Question ───────────────────────► Answer
v2.0:  Question ──► Plan ──► Execution ──► Answer
                     ↓          ↓
              [可蒸馏内容]  [可蒸馏内容]
```

### 4.2 训练数据格式 (ShareGPT/OpenAI Format)

#### 4.2.1 Factual QA (单跳)

```json
{
  "id": "distill_factual_001",
  "timestamp": "2026-01-28T19:00:00+08:00",
  "conversations": [
    {
      "role": "system",
      "content": "你是一个原神剧情专家 Agent。基于给定的参考资料回答问题。"
    },
    {
      "role": "user",
      "content": "【参考资料】\n（原始文本段落：玛拉妮在流泉之众聚落中心的对话...）\n\n【用户问题】\n玛拉妮的性格有什么特点？"
    },
    {
      "role": "assistant",
      "content": "<plan>\n策略: vector_single_hop\n步骤: embed → search → rerank\n</plan>\n<think>\n参考资料中，玛拉妮与卡齐娜的对话显示她...（Teacher 蒸馏的推理过程）\n</think>\n玛拉妮性格热情直率，喜欢探险和挑战..."
    }
  ],
  "metadata": {
    "question_type": "factual",
    "retrieval_strategy": "vector_single_hop",
    "golden_context_file": "Data/natlan/chapter1_dialogue.txt"
  }
}
```

#### 4.2.2 Relationship QA (图增强)

```json
{
  "id": "distill_relation_001",
  "timestamp": "2026-01-28T19:05:00+08:00",
  "conversations": [
    {
      "role": "system",
      "content": "你是一个原神剧情专家 Agent。对于关系类问题，需要整合多个场景的信息。"
    },
    {
      "role": "user",
      "content": "【参考资料 1 - 竞技场场景】\n（原始文本...恰斯卡与卡齐娜并肩作战...）\n\n【参考资料 2 - 庆功宴场景】\n（原始文本...两人在宴会上交谈...）\n\n【用户问题】\n恰斯卡和卡齐娜是什么关系？"
    },
    {
      "role": "assistant",
      "content": "<plan>\n策略: graph_augmented\n步骤:\n1. extract_entities: [恰斯卡, 卡齐娜]\n2. graph_traverse: depth=2, relations=[friend_of, teammate]\n3. vector_search: filter=related_scenes\n4. aggregate_multi_source\n</plan>\n<think>\n从参考资料1可知，她们在竞技场并肩作战，表明是战友关系...\n从参考资料2可知，庆功宴上的亲密交谈进一步证实了朋友关系...\n整合判断：战友 + 朋友\n</think>\n恰斯卡和卡齐娜是战友兼朋友的关系。她们在竞技场共同战斗，建立了深厚的战友情谊，在庆功宴等日常场景中也表现出亲密的朋友关系。"
    }
  ],
  "metadata": {
    "question_type": "relationship",
    "retrieval_strategy": "graph_augmented",
    "relationship_triple": {
      "subject": "恰斯卡",
      "relation": ["friend_of", "teammate"],
      "object": "卡齐娜"
    },
    "context_sources": 2
  }
}
```

#### 4.2.3 Tracking QA (时序多跳)

```json
{
  "id": "distill_tracking_001",
  "timestamp": "2026-01-28T19:10:00+08:00",
  "conversations": [
    {
      "role": "system",
      "content": "你是一个原神剧情专家 Agent。对于事件追踪类问题，需要按时间顺序整合多个章节的信息。"
    },
    {
      "role": "user",
      "content": "【参考资料 1 - 第一章：初入纳塔】\n（原始文本...旅行者初次到达纳塔...）\n\n【参考资料 2 - 第三章：竞技场报名】\n（原始文本...旅行者在古名竞技场报名...）\n\n【参考资料 3 - 第五章：试炼胜利】\n（原始文本...旅行者赢得试炼...）\n\n【参考资料 4 - 第六章：授予古名】\n（原始文本...纳塔长老授予旅行者古名...）\n\n【用户问题】\n旅行者在纳塔是通过什么方式获得古名的？"
    },
    {
      "role": "assistant",
      "content": "<plan>\n策略: temporal_multi_hop\n步骤:\n1. decompose_to_milestones: [初入纳塔, 竞技场报名, 试炼胜利, 授予古名]\n2. sequential_retrieval: 按章节顺序检索\n3. temporal_ordering: 验证时间线一致性\n4. synthesize_timeline: 合成完整叙事\n</plan>\n<think>\n时间线分析：\n- T1(第一章): 旅行者到达纳塔，此时没有古名\n- T2(第三章): 为获得古名，报名参加竞技场试炼\n- T3(第五章): 经过激烈战斗赢得试炼\n- T4(第六章): 纳塔长老正式授予古名\n结论: 核心方式是「参加并赢得竞技场试炼」\n</think>\n旅行者在纳塔通过参加古名竞技场试炼的方式获得了古名。具体过程是：在到达纳塔后报名参加竞技场（第三章），经过一系列激烈的战斗赢得试炼（第五章），最终由纳塔长老正式授予古名（第六章）。"
    }
  ],
  "metadata": {
    "question_type": "tracking",
    "retrieval_strategy": "temporal_multi_hop",
    "timeline_milestones": ["初入纳塔", "竞技场报名", "试炼胜利", "授予古名"],
    "context_hops": 4
  }
}
```

#### 4.2.4 Multi-turn QA (指代消解)

```json
{
  "id": "distill_multiturn_001",
  "timestamp": "2026-01-28T19:15:00+08:00",
  "conversations": [
    {
      "role": "system",
      "content": "你是一个原神剧情专家 Agent。在多轮对话中需要正确理解指代词（他/她/它等）。"
    },
    {
      "role": "user",
      "content": "基尼奇的龙伙伴叫什么？"
    },
    {
      "role": "assistant",
      "content": "<plan>\n策略: vector_single_hop\n实体标记: [基尼奇 → Character, 龙伙伴 → Entity]\n</plan>\n基尼奇的龙伙伴叫阿尤。"
    },
    {
      "role": "user",
      "content": "【参考资料】\n（原始文本...基尼奇与阿尤一起战斗...阿尤喷出火焰攻击深渊魔物...）\n\n在这个任务中"它"做了什么？"
    },
    {
      "role": "assistant",
      "content": "<plan>\n策略: session_aware\n步骤:\n1. resolve_coreference: \"它\" → 上文实体 \"阿尤\"\n2. rewrite_query: \"在这个任务中阿尤做了什么？\"\n3. vector_search: filter=current_scene\n</plan>\n<think>\n指代消解：\n- \"它\" 在上下文中指代上一轮提到的 \"阿尤\"（基尼奇的龙伙伴）\n- 改写问题为 \"在这个任务中阿尤做了什么？\"\n\n从参考资料中：阿尤与基尼奇并肩作战，使用火焰攻击深渊魔物\n</think>\n在这个任务中，阿尤（基尼奇的龙伙伴）协助基尼奇战斗，使用火焰攻击击退了深渊魔物。"
    }
  ],
  "metadata": {
    "question_type": "multiturn",
    "retrieval_strategy": "session_aware",
    "coreference_resolution": {
      "pronoun": "它",
      "referent": "阿尤",
      "source_turn": 1
    }
  }
}
```

---

## 5. 实施计划与时间线

### 5.1 Phase 1: 基础设施 (Week 1-2)

| 时间戳 | 里程碑 | 交付物 |
|--------|--------|--------|
| 2026-02-01T00:00:00 | MVP RAG Pipeline 完成 | 单跳向量检索可用 |
| 2026-02-03T00:00:00 | Intent Classifier 训练 | 5类问题分类器 |
| 2026-02-07T00:00:00 | Planner Agent v0.1 | 基础计划生成逻辑 |

### 5.2 Phase 2: 多策略检索 (Week 3-4)

| 时间戳 | 里程碑 | 交付物 |
|--------|--------|--------|
| 2026-02-10T00:00:00 | Graph Retriever 集成 | Neo4j + LlamaIndex 打通 |
| 2026-02-14T00:00:00 | Temporal Retriever 实现 | 跨章节多跳检索 |
| 2026-02-17T00:00:00 | Session Memory 实现 | 指代消解 + 滑动窗口 |

### 5.3 Phase 3: 蒸馏与训练 (Week 5-6)

| 时间戳 | 里程碑 | 交付物 |
|--------|--------|--------|
| 2026-02-20T00:00:00 | Teacher 数据生成 | 500+ 蒸馏样本 |
| 2026-02-24T00:00:00 | SFT 训练完成 | 微调后的 Planner Agent |
| 2026-02-28T00:00:00 | 端到端评测 | RAGAS 评测报告 |

### 5.4 Phase 4: 优化迭代 (Week 7-8)

| 时间戳 | 里程碑 | 交付物 |
|--------|--------|--------|
| 2026-03-03T00:00:00 | 错误分析 & 数据增强 | 针对性补充训练数据 |
| 2026-03-07T00:00:00 | DPO 偏好优化 | 更精准的计划生成 |
| 2026-03-10T00:00:00 | 最终版本发布 | v1.0 Release |

---

## 6. 技术选型确认

### 6.1 Plan-Based Memory vs Pure GraphRAG

| 方面 | Pure GraphRAG | Plan-Based Memory (选定) |
|------|---------------|--------------------------|
| 灵活性 | 低（固定图结构） | 高（动态计划生成） |
| 时序支持 | 弱 | 强（显式时间线处理） |
| 多跳推理 | 依赖预构建路径 | 按需多跳 |
| 可解释性 | 中 | 高（显式 Plan 输出） |
| 训练复杂度 | 低 | 中（需蒸馏 Plan） |

**选择理由**: 原神剧情涉及复杂的角色关系、时间线演变，需要灵活的检索策略而非固定的图遍历。

### 6.2 Agent 训练方法

| 方法 | 适用场景 | 我们的选择 |
|------|----------|------------|
| SFT (Supervised Fine-Tuning) | 基础能力习得 | ✅ Phase 3 主要方法 |
| DPO (Direct Preference Optimization) | 偏好对齐 | ✅ Phase 4 优化 |
| RLHF | 复杂对齐 | ❌ 成本过高 |
| RAG-only (无微调) | 快速原型 | ✅ Phase 1 MVP |

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Planner 生成错误计划 | 检索失败 | 加入 Plan Validator，错误时 fallback 到默认策略 |
| 多跳检索延迟过高 | 用户体验差 | 设置最大跳数限制 (max_hops=4)，并行执行子查询 |
| 蒸馏数据质量不一致 | 训练效果差 | Teacher 使用 Claude Opus 4.5，多轮验证 |
| 指代消解准确率低 | 多轮对话出错 | 显式实体跟踪，每轮更新 Entity Cache |

---

## 8. 下一步行动

1. **立即**: 完成 Intent Classifier 的 5 类标签定义
2. **本周**: 设计 Planner Agent 的 Prompt Template
3. **下周**: 开始用 Teacher Model 生成第一批蒸馏数据 (50 条)
4. **持续**: 建立 Golden Dataset 与蒸馏数据的版本对应关系

---

## 附录 A: 文件更新记录

| 时间戳 | 版本 | 变更内容 |
|--------|------|----------|
| 2026-01-28T14:54:00+08:00 | v1.0 | 初始版本：Context-Grounded Distillation |
| 2026-01-28T18:55:00+08:00 | v2.0 | 新增：多智能体架构、Plan-Based Memory、详细时间线 |
