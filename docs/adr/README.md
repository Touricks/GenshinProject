# Architecture Decision Records (ADR)

> 架构决策记录 | Architecture Decision Records

本目录记录系统架构中的重要技术决策，便于追溯和新成员理解系统设计背景。

---

## ADR 索引

| ADR | 状态 | 决策 | 日期 |
|-----|------|------|------|
| [ADR-006](./ADR-006-tool-design.md) | `Approved` | 确定 4 个核心检索工具 + LlamaIndex FunctionAgent | 2026-01-28 |

### 历史 ADR (已被取代)

| ADR | 状态 | 原决策 | 取代原因 |
|-----|------|--------|----------|
| ADR-001 ~ ADR-005 | `Superseded` | DPO/DAPO/ReAct 训练方案 | 改用 Function Calling，无需 SFT |

---

## ADR 模板

```markdown
# ADR-[编号]: [标题]

> **状态**: Proposed | Approved | Deprecated | Superseded
> **创建时间**: YYYY-MM-DD
> **修订时间**: YYYY-MM-DD
> **决策者**: [Name]

## Context (背景)

描述导致此决策的背景和问题。

## Decision (决策)

描述做出的决策。

## Rationale (理由)

解释为什么选择这个方案。

## Alternatives Considered (备选方案)

列出考虑过的其他方案及其优缺点。

## Consequences (后果)

### Positive (正面)
- ...

### Negative (负面)
- ...

## References (参考)

- 相关文档链接
- 讨论记录链接
```

---

## ADR 状态流转

```
Proposed ──► Approved ──► Deprecated
                │
                └──► Superseded (by new ADR)
```

---

## 何时需要 ADR

- 选择核心技术栈
- 确定系统架构模式
- 重大 API 设计决策
- 弃用现有功能或组件
- 引入新的外部依赖
