# Design Documents

> 设计文档目录 | Technical Design Documents

本目录包含系统的技术设计文档，遵循 Google Design Doc 规范。

---

## 文档列表

| 文档 | 状态 | 说明 |
|------|------|------|
| [system-architecture.md](./system-architecture.md) | `Approved` | 系统架构 & 技术选型 |
| [data-pipeline.md](./data-pipeline.md) | `Draft` | 数据处理流水线设计 |
| [data-model.md](./data-model.md) | `Draft` | Neo4j 图数据库 Schema |

---

## Google Design Doc 规范

每个设计文档应包含以下部分：

```markdown
# [Feature/System Name] Design Doc

> Status: Draft | In Review | Approved
> Author: [Name]
> Last Updated: [Date]
> Reviewers: [Names]

## 1. Overview (概述)
- 背景和动机
- 目标和非目标

## 2. Background (背景)
- 相关系统和依赖
- 现有解决方案的问题

## 3. Design (设计)
- 高层架构
- 详细设计
- API 定义
- 数据模型

## 4. Alternatives Considered (备选方案)
- 其他考虑过的方案
- 为什么选择当前方案

## 5. Cross-cutting Concerns (横切关注点)
- 安全性
- 性能
- 可扩展性
- 可测试性

## 6. Implementation Plan (实施计划)
- 里程碑
- 依赖关系

## 7. Open Questions (待解决问题)
- 需要进一步讨论的问题
```

---

## 文档关系

```
system-architecture.md (技术栈 & 整体架构)
         │
         ├──► data-pipeline.md (数据处理详细设计)
         │
         └──► data-model.md (数据模型详细设计)
```
