# Graph Query Tools 工作原理

> Agent 调用 Neo4j 知识图谱的查询方法文档

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent (ReAct)                            │
├─────────────────────────────────────────────────────────────────┤
│  lookup_knowledge  │ find_connection │ track_journey │ get_character_events │
├────────────────────┴─────────────────┴───────────────┴──────────┤
│                      GraphSearcher                              │
│  ┌──────────┐ ┌─────────────────┐ ┌──────────────┐ ┌───────────┐│
│  │ search() │ │get_path_between │ │search_history│ │get_major_ ││
│  │          │ │       ()        │ │     ()       │ │ events()  ││
│  └────┬─────┘ └───────┬─────────┘ └──────┬───────┘ └─────┬─────┘│
│       │               │                  │               │      │
│       └───────────────┴──────────────────┴───────────────┘      │
│                           │                                      │
│               _resolve_canonical_name()                          │
│                   (Fulltext Index)                               │
├─────────────────────────────────────────────────────────────────┤
│                      Neo4jConnection                            │
│                         (Cypher)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │    Neo4j      │
                      │  (Port 7687)  │
                      └───────────────┘
```

---

## 1. lookup_knowledge

**用途**：查询实体的静态信息和直接关系

### 调用链

```
lookup_knowledge(entity, relation)
    └── GraphSearcher.search(entity, relation, limit=10)
            ├── _resolve_canonical_name(entity)  # 别名解析
            └── Cypher: MATCH (a {name})-[r]-(b) RETURN ...
```

### 底层 API

```python
GraphSearcher.search(
    entity: str,           # 实体名（支持别名）
    relation: Optional[str] = None,  # 关系类型过滤
    depth: int = 1,        # 搜索深度（暂未实现）
    limit: int = 20        # 最大结果数
) -> Dict[str, Any]
```

### Cypher 查询

**无关系过滤**：
```cypher
MATCH (a {name: $entity})-[r]-(b)
RETURN
    a.name as source,
    type(r) as relation,
    b.name as target,
    labels(b)[0] as target_type,
    b.description as description,
    properties(r) as rel_properties
LIMIT $limit
```

**有关系过滤**（动态构建）：
```cypher
MATCH (a {name: $entity})-[r:FRIEND_OF]-(b)
RETURN ...
LIMIT $limit
```

### 适用问题

| 问题示例 | 参数 |
|---------|------|
| "少女是谁？" | `entity="少女"` |
| "玛薇卡的称号是什么？" | `entity="玛薇卡"` |
| "基尼奇的朋友有谁？" | `entity="基尼奇", relation="FRIEND_OF"` |
| "恰斯卡属于什么组织？" | `entity="恰斯卡", relation="MEMBER_OF"` |

### 返回格式

```markdown
## 实体信息：少女

- [FRIEND_OF] → 旅行者 (Character) [第160章, 任务1607]
- [EXPERIENCES] → 献出身体 (MajorEvent): 少女将身体化作月光...
- [MEMBER_OF] → 希汐岛 (Organization)

共找到 10 条关系。
```

---

## 2. find_connection

**用途**：查找两个实体之间的最短路径

### 调用链

```
find_connection(entity1, entity2)
    └── GraphSearcher.get_path_between(entity1, entity2)
            ├── _resolve_canonical_name(entity1)
            ├── _resolve_canonical_name(entity2)
            └── Cypher: shortestPath(...) [max 4 hops]
```

### 底层 API

```python
GraphSearcher.get_path_between(
    entity1: str,  # 起点实体
    entity2: str   # 终点实体
) -> Optional[Dict[str, Any]]
```

### Cypher 查询

```cypher
MATCH path = shortestPath(
    (a {name: $entity1})-[*..4]-(b {name: $entity2})
)
WHERE none(n in nodes(path) WHERE n:Region OR n:Nation)
RETURN
    [n in nodes(path) | n.name] as path_nodes,
    [r in relationships(path) | type(r)] as path_relations,
    length(path) as path_length
```

**注意**：
- 最大深度 4 跳
- 排除 `Region` 和 `Nation` 节点（避免无意义路径）

### 适用问题

| 问题示例 | 参数 |
|---------|------|
| "努昂诺塔和少女是什么关系？" | `entity1="努昂诺塔", entity2="少女"` |
| "恰斯卡怎么认识旅行者？" | `entity1="恰斯卡", entity2="旅行者"` |
| "基尼奇和玛薇卡有联系吗？" | `entity1="基尼奇", entity2="玛薇卡"` |

### 返回格式

```markdown
## 关系路径：恰斯卡 ↔ 旅行者

**路径**（2 步）：
恰斯卡 -[MEMBER_OF]-> 花羽会 -[ALLIED_WITH]-> 旅行者

**路径中的节点：**
- 恰斯卡
- 花羽会
- 旅行者
```

---

## 3. track_journey

**用途**：追踪实体的关系变化历程（时间线）

### 调用链

```
track_journey(entity, target)
    └── GraphSearcher.search_history(entity, target)
            ├── _resolve_canonical_name(entity)
            ├── _resolve_canonical_name(target)  # if provided
            └── Cypher: MATCH ... ORDER BY chapter, task_id ASC
```

### 底层 API

```python
GraphSearcher.search_history(
    entity: str,                    # 主要实体
    target: Optional[str] = None    # 特定关系对象过滤
) -> List[Dict[str, Any]]
```

### Cypher 查询

```cypher
MATCH (a)-[r]->(b)
WHERE a.name = $source [AND b.name = $target]
RETURN
    a.name as source,
    b.name as target,
    type(r) as relation,
    r.chapter as chapter,
    r.task_id as task_id,
    r.evidence as evidence
ORDER BY r.chapter ASC, r.task_id ASC
```

**关键点**：
- 返回按时间顺序排列的关系事件
- 边上存储 `chapter`, `task_id`, `evidence` 属性

### 适用问题

| 问题示例 | 参数 |
|---------|------|
| "旅行者在纳塔的经历" | `entity="旅行者"` |
| "少女和努昂诺塔的关系如何发展？" | `entity="少女", target="努昂诺塔"` |
| "基尼奇的组织隶属变化" | `entity="基尼奇"` |

### 返回格式

```markdown
## 时间线：少女
（与 努昂诺塔 的关系）

### 第 1607 章
- [CREATES] → 努昂诺塔 (任务: 16071040)
  > 证据: 少女将一部分力量分出，创造了努昂诺塔...

### 第 1608 章
- [REUNITES_WITH] → 努昂诺塔 (任务: 16080130)
  > 证据: 少女与努昂诺塔重逢...

共找到 2 条关系事件。

**提示**: 如需详细剧情内容，请使用 search_memory 搜索此时间线中的特定事件。
```

---

## 4. get_character_events

**用途**：获取角色的重大事件/转折点（MajorEvent 节点）

### 调用链

```
get_character_events(entity, event_type)
    └── GraphSearcher.get_major_events(entity, event_type, limit=20)
            ├── _resolve_canonical_name(entity)
            └── Cypher: MATCH (c)-[r:EXPERIENCES]->(e:MajorEvent) ...
```

### 底层 API

```python
GraphSearcher.get_major_events(
    entity: str,                      # 角色名
    event_type: Optional[str] = None, # 事件类型过滤
    limit: int = 20                   # 最大结果数
) -> List[Dict[str, Any]]
```

### Cypher 查询

```cypher
MATCH (c:Character {name: $entity})-[r:EXPERIENCES]->(e:MajorEvent)
[WHERE e.event_type = $event_type]
RETURN e.name as event_name,
       e.event_type as event_type,
       e.chapter as chapter,
       e.task_id as task_id,
       e.summary as summary,
       e.evidence as evidence,
       r.role as role,
       r.outcome as outcome
ORDER BY e.chapter ASC
LIMIT $limit
```

### 事件类型分类

| Type | 中文 | 描述 | 示例 |
|------|------|------|------|
| `sacrifice` | 牺牲 | 角色付出重大代价 | 少女献出身体 |
| `transformation` | 转变 | 角色状态/形态改变 | 少女化作月光 |
| `acquisition` | 获得 | 角色获得力量/物品 | 少女获得三月权能 |
| `loss` | 失去 | 角色失去某物/某人 | 姐姐们失去权能 |
| `encounter` | 相遇 | 重要人物相遇 | 旅行者遇见少女 |
| `conflict` | 冲突 | 战斗/对抗 | 对抗多托雷 |
| `revelation` | 揭示 | 真相/秘密揭露 | 身份揭示 |
| `milestone` | 里程碑 | 重要转折点 | 进入月亮倒影 |

### 设计动机：语义鸿沟问题

```
用户问: "少女是如何重回世界的"
        ↓
关键词: "重回世界" ← 数据库无此记录
        ↓
但数据库有: "献出身体", "权能转交", "化作月光"
        ↓
get_character_events 返回这些具体事件
        ↓
Agent 用事件摘要综合回答问题
```

### 适用问题

| 问题示例 | 参数 |
|---------|------|
| "少女经历了什么？" | `entity="少女"` |
| "少女是如何重回世界的？" | `entity="少女"` |
| "谁牺牲了？" | `event_type="sacrifice"` |
| "旅行者获得了什么？" | `entity="旅行者", event_type="acquisition"` |

### 返回格式

```markdown
## 重大事件：少女

### 第 1607 章

**少女献出身体** [牺牲] (主动)
  - 摘要: 少女将身体化作月光洒向挪德卡莱
  - 结果: transformation
  - 证据: "在那一刻，她选择了献出一切..."

**少女获得三月权能** [获得] (被动)
  - 摘要: 少女继承了三月的力量
  - 结果: power_gain
  - 证据: "月矩力流入她的体内..."

共找到 5 个重大事件。

**提示**: 如需详细剧情内容，请使用 search_memory 搜索特定事件。
```

---

## 核心机制：别名解析

所有图查询方法都通过 `_resolve_canonical_name()` 进行别名解析。

### 工作流程

```
输入: "火神"
    ↓
Fulltext Search: db.index.fulltext.queryNodes("entity_alias_index", "火神")
    ↓
结果: [{name: "玛薇卡", aliases: ["火神", "Mavuika"], score: 0.95}, ...]
    ↓
选择策略:
  1. 优先选择有 aliases 的节点（Seed Character）
  2. 其次按 score 最高选择
    ↓
输出: "玛薇卡"
```

### Cypher 查询

```cypher
CALL db.index.fulltext.queryNodes("entity_alias_index", $name)
YIELD node, score
RETURN node.name as name, node.aliases as aliases, score
LIMIT 5
```

---

## 工具选择指南

| 问题类型 | 推荐工具 | 示例 |
|---------|---------|------|
| "X是谁？" | `lookup_knowledge` | 基本信息查询 |
| "X的Y是什么？" | `lookup_knowledge` | 属性查询 |
| "X和Y是什么关系？" | `find_connection` | 路径查询 |
| "X经历了什么？" | `track_journey` 或 `get_character_events` | 历程查询 |
| "X是如何做到Y的？" | `get_character_events` | 事件查询 |
| "发生了什么Z事件？" | `get_character_events(event_type=Z)` | 事件类型查询 |

---

## 图数据结构

### 节点类型

| Label | Count | 描述 |
|-------|-------|------|
| Character | 276 | 角色实体 |
| Organization | 12 | 组织实体 |
| MajorEvent | TBD | 重大事件节点 |

### 关系类型

| Relation | Count | 描述 |
|----------|-------|------|
| PARTNER_OF | 207 | 搭档关系 |
| MEMBER_OF | 194 | 组织成员 |
| FRIEND_OF | 132 | 朋友关系 |
| INTERACTS_WITH | 107 | 互动关系 |
| ENEMY_OF | 87 | 敌对关系 |
| FAMILY_OF | 63 | 家庭关系 |
| LEADER_OF | 46 | 领导关系 |
| EXPERIENCES | TBD | 角色经历事件 |

---

## 源码位置

| 文件 | 功能 |
|------|------|
| `src/graph/searcher.py` | GraphSearcher 类，所有底层查询方法 |
| `src/retrieval/lookup_knowledge.py` | lookup_knowledge 工具封装 |
| `src/retrieval/find_connection.py` | find_connection 工具封装 |
| `src/retrieval/track_journey.py` | track_journey 工具封装 |
| `src/retrieval/get_character_events.py` | get_character_events 工具封装 |
