# Neo4j Schema Design

> **状态**: Draft
> **创建时间**: 2026-01-29
> **关联文档**: ADR-006-final-tool-design.md, data-pipeline-design.md

---

## 1. 设计目标

为 `graph_search` 工具提供支持，处理以下查询类型：

| 查询类型 | 示例 | 所需结构 |
|----------|------|----------|
| 关系查询 | "恰斯卡和卡齐娜是什么关系？" | Character → Relation → Character |
| 社交网络 | "基尼奇的朋友有谁？" | Character → FRIEND_OF → Character |
| 组织成员 | "流泉之众有哪些成员？" | Character → MEMBER_OF → Organization |
| 事件参与 | "谁参与了竞技场试炼？" | Character → PARTICIPATED_IN → Event |

---

## 2. Node 类型

### 2.1 Character (角色)

```cypher
(:Character {
    name: STRING,              -- "恰斯卡", "基尼奇"
    aliases: [STRING],         -- ["杜麦尼", "旅行者"] (别名)
    title: STRING,             -- "花羽会族长", "龙骑士"
    region: STRING,            -- "纳塔", "须弥"
    tribe: STRING,             -- "花羽会", "竞人族"
    description: STRING,       -- 简短描述
    first_appearance_chapter: INTEGER  -- 首次出现章节
})
```

**主要角色列表:**

| 角色 | aliases | tribe | description |
|------|---------|-------|-------------|
| 恰斯卡 | [] | 花羽会 | 花羽会的族长，善于使用弓箭 |
| 卡齐娜 | [] | 流泉之众 | 年轻的大地岩手，性格活泼 |
| 玛拉妮 | [] | 流泉之众 | 神之子候选人，温柔善良 |
| 基尼奇 | [] | 竞人族 | 年轻的龙骑士，沉默寡言 |
| 阿尤 | [] | - | 基尼奇的龙伙伴 |
| 希诺宁 | [] | 流泉之众 | 死之国的引路人 |
| 旅行者 | [玩家, 杜麦尼] | - | 来自异世界的旅行者 |
| 派蒙 | [] | - | 旅行者的向导 |

### 2.2 Organization (组织/部族)

```cypher
(:Organization {
    name: STRING,              -- "花羽会", "流泉之众"
    type: STRING,              -- "tribe", "guild", "nation"
    region: STRING,            -- "纳塔"
    description: STRING
})
```

**主要组织:**
- 花羽会 (tribe)
- 流泉之众 (tribe)
- 竞人族 (tribe)
- 金鳞会 (tribe)
- 纳塔 (nation)

### 2.3 Location (地点)

```cypher
(:Location {
    name: STRING,              -- "竞技场", "花羽会领地"
    type: STRING,              -- "arena", "settlement", "landmark"
    region: STRING,            -- "纳塔"
    description: STRING
})
```

### 2.4 Event (事件)

```cypher
(:Event {
    name: STRING,              -- "竞技场试炼", "深渊入侵"
    type: STRING,              -- "battle", "ceremony", "quest"
    chapter_range: [INTEGER],  -- [1, 3] (跨越章节)
    description: STRING
})
```

### 2.5 Chunk (文本块 - 连接向量库)

```cypher
(:Chunk {
    chunk_id: STRING,          -- 对应 Qdrant 中的 ID
    event_order: INTEGER,      -- 用于时序排序
    task_id: STRING,
    chapter_number: INTEGER
})
```

---

## 3. Relationship 类型

### 3.1 社交关系

```cypher
-- 朋友关系
(:Character)-[:FRIEND_OF {
    since_chapter: INTEGER,    -- 建立友谊的章节
    strength: STRING           -- "close", "acquaintance"
}]->(:Character)

-- 敌对关系
(:Character)-[:ENEMY_OF {
    reason: STRING,            -- "战斗", "信仰冲突"
    resolved: BOOLEAN          -- 是否已和解
}]->(:Character)

-- 伙伴关系 (特殊)
(:Character)-[:PARTNER_OF {
    type: STRING               -- "dragon_partner", "travel_companion"
}]->(:Character)
```

### 3.2 组织关系

```cypher
-- 成员关系
(:Character)-[:MEMBER_OF {
    role: STRING,              -- "leader", "member", "elder"
    since_chapter: INTEGER
}]->(:Organization)

-- 组织从属
(:Organization)-[:PART_OF]->(:Organization)
```

### 3.3 事件关系

```cypher
-- 参与事件
(:Character)-[:PARTICIPATED_IN {
    role: STRING               -- "protagonist", "antagonist", "support"
}]->(:Event)

-- 事件发生地点
(:Event)-[:OCCURRED_AT]->(:Location)

-- 事件包含文本
(:Event)-[:CONTAINS]->(:Chunk)
```

### 3.4 时序关系

```cypher
-- 事件先后顺序
(:Event)-[:LEADS_TO]->(:Event)

-- Chunk 先后顺序
(:Chunk)-[:NEXT]->(:Chunk)
```

---

## 4. 完整 Schema 可视化

```
                    ┌─────────────┐
                    │ Organization│
                    │  (部族)     │
                    └──────┬──────┘
                           │ MEMBER_OF
                           │
┌─────────────┐    ┌───────┴───────┐    ┌─────────────┐
│  Location   │◄───│   Character   │───►│  Character  │
│   (地点)    │    │    (角色)     │    │   (角色)    │
└─────────────┘    └───────┬───────┘    └─────────────┘
       ▲                   │                    │
       │ OCCURRED_AT       │ PARTICIPATED_IN   │ FRIEND_OF
       │                   │                   │ ENEMY_OF
       │                   ▼                   │ PARTNER_OF
       │           ┌───────────────┐           │
       └───────────│     Event     │◄──────────┘
                   │    (事件)     │
                   └───────┬───────┘
                           │ CONTAINS
                           ▼
                   ┌───────────────┐
                   │     Chunk     │
                   │  (文本块)     │
                   └───────────────┘
```

---

## 5. 初始数据导入

### 5.1 角色导入脚本

```cypher
// 创建主要角色
CREATE (:Character {
    name: '恰斯卡',
    title: '花羽会族长',
    region: '纳塔',
    tribe: '花羽会',
    description: '花羽会的年轻族长，精通弓术和飞行'
});

CREATE (:Character {
    name: '卡齐娜',
    region: '纳塔',
    tribe: '流泉之众',
    description: '年轻的大地岩手，性格活泼开朗'
});

CREATE (:Character {
    name: '基尼奇',
    region: '纳塔',
    tribe: '竞人族',
    description: '年轻的龙骑士，与龙阿尤是伙伴'
});

CREATE (:Character {
    name: '阿尤',
    description: '基尼奇的龙伙伴，喜欢学舌'
});

CREATE (:Character {
    name: '旅行者',
    aliases: ['玩家', '杜麦尼'],
    description: '来自异世界的旅行者，在纳塔获得了古名杜麦尼'
});

CREATE (:Character {
    name: '派蒙',
    description: '旅行者的向导，飞行的小精灵'
});

CREATE (:Character {
    name: '玛拉妮',
    region: '纳塔',
    tribe: '流泉之众',
    description: '神之子候选人，温柔善良的水疗师'
});

CREATE (:Character {
    name: '希诺宁',
    region: '纳塔',
    tribe: '流泉之众',
    description: '死之国的引路人'
});

CREATE (:Character {
    name: '伊法',
    region: '纳塔',
    tribe: '花羽会',
    description: '花羽会的医生'
});

CREATE (:Character {
    name: '咔库库',
    description: '伊法的助理，一只会学舌的小龙'
});
```

### 5.2 组织导入

```cypher
// 创建组织
CREATE (:Organization {name: '花羽会', type: 'tribe', region: '纳塔'});
CREATE (:Organization {name: '流泉之众', type: 'tribe', region: '纳塔'});
CREATE (:Organization {name: '竞人族', type: 'tribe', region: '纳塔'});
CREATE (:Organization {name: '金鳞会', type: 'tribe', region: '纳塔'});
CREATE (:Organization {name: '纳塔', type: 'nation'});
```

### 5.3 关系导入

```cypher
// 成员关系
MATCH (c:Character {name: '恰斯卡'}), (o:Organization {name: '花羽会'})
CREATE (c)-[:MEMBER_OF {role: 'leader'}]->(o);

MATCH (c:Character {name: '伊法'}), (o:Organization {name: '花羽会'})
CREATE (c)-[:MEMBER_OF {role: 'member'}]->(o);

MATCH (c:Character {name: '卡齐娜'}), (o:Organization {name: '流泉之众'})
CREATE (c)-[:MEMBER_OF {role: 'member'}]->(o);

MATCH (c:Character {name: '玛拉妮'}), (o:Organization {name: '流泉之众'})
CREATE (c)-[:MEMBER_OF {role: 'member'}]->(o);

MATCH (c:Character {name: '基尼奇'}), (o:Organization {name: '竞人族'})
CREATE (c)-[:MEMBER_OF {role: 'member'}]->(o);

// 友谊关系
MATCH (a:Character {name: '恰斯卡'}), (b:Character {name: '卡齐娜'})
CREATE (a)-[:FRIEND_OF {strength: 'close'}]->(b);

MATCH (a:Character {name: '旅行者'}), (b:Character {name: '派蒙'})
CREATE (a)-[:PARTNER_OF {type: 'travel_companion'}]->(b);

MATCH (a:Character {name: '基尼奇'}), (b:Character {name: '阿尤'})
CREATE (a)-[:PARTNER_OF {type: 'dragon_partner'}]->(b);

// 所有主角都是朋友 (简化)
MATCH (a:Character), (b:Character)
WHERE a.name IN ['恰斯卡', '卡齐娜', '玛拉妮', '基尼奇', '希诺宁']
  AND b.name IN ['恰斯卡', '卡齐娜', '玛拉妮', '基尼奇', '希诺宁']
  AND a.name < b.name
CREATE (a)-[:FRIEND_OF {strength: 'acquaintance'}]->(b);
```

---

## 6. graph_search 工具实现

### 6.1 Cypher 查询模板

```python
QUERY_TEMPLATES = {
    # 查询实体的所有关系
    "all_relations": """
        MATCH (a:Character {name: $entity})-[r]-(b)
        RETURN a.name as source, type(r) as relation, b.name as target, labels(b) as target_type
        LIMIT 20
    """,

    # 查询特定类型关系
    "specific_relation": """
        MATCH (a:Character {name: $entity})-[r:$relation_type*1..$depth]-(b:Character)
        RETURN DISTINCT b.name as name, b.description as description
        LIMIT 20
    """,

    # 查询组织成员
    "org_members": """
        MATCH (c:Character)-[:MEMBER_OF]->(o:Organization {name: $entity})
        RETURN c.name as name, c.title as title, c.description as description
    """,

    # 查询两个实体之间的关系路径
    "path_between": """
        MATCH path = shortestPath((a:Character {name: $entity1})-[*..4]-(b:Character {name: $entity2}))
        RETURN [n in nodes(path) | n.name] as path_nodes,
               [r in relationships(path) | type(r)] as path_relations
    """,

    # 查询角色参与的事件
    "participated_events": """
        MATCH (c:Character {name: $entity})-[:PARTICIPATED_IN]->(e:Event)
        RETURN e.name as event, e.description as description, e.chapter_range as chapters
    """
}
```

### 6.2 Python 实现

```python
from neo4j import GraphDatabase
from typing import List, Dict, Optional

class GraphSearcher:
    def __init__(self, uri: str = "bolt://localhost:7687"):
        self.driver = GraphDatabase.driver(uri)

    def search(
        self,
        entity: str,
        relation: Optional[str] = None,
        depth: int = 2
    ) -> List[Dict]:
        """
        graph_search 工具的核心实现

        Args:
            entity: 起始实体名称
            relation: 关系类型 (None 表示所有关系)
            depth: 遍历深度

        Returns:
            相关实体和关系列表
        """
        with self.driver.session() as session:
            if relation:
                # 查询特定关系
                query = f"""
                    MATCH (a {{name: $entity}})-[r:{relation}*1..{depth}]-(b)
                    RETURN DISTINCT
                        a.name as source,
                        type(r) as relation,
                        b.name as target,
                        labels(b)[0] as target_type,
                        b.description as description
                    LIMIT 20
                """
            else:
                # 查询所有关系
                query = f"""
                    MATCH (a {{name: $entity}})-[r*1..{depth}]-(b)
                    RETURN DISTINCT
                        a.name as source,
                        type(r) as relation,
                        b.name as target,
                        labels(b)[0] as target_type,
                        b.description as description
                    LIMIT 20
                """

            result = session.run(query, entity=entity)
            records = [dict(record) for record in result]

        # 获取相关 Chunk (从 Qdrant)
        related_chunks = self._fetch_related_chunks(records)

        return {
            "entities": records,
            "chunks": related_chunks
        }

    def _fetch_related_chunks(self, entities: List[Dict]) -> List[Dict]:
        """从 Qdrant 获取相关实体的文本 Chunk"""
        entity_names = list(set(
            [e["source"] for e in entities] +
            [e["target"] for e in entities]
        ))

        # 调用 Qdrant 按 entity_filter 检索
        # 实际实现在 vector_search 中
        return []

    def close(self):
        self.driver.close()
```

---

## 7. 索引优化

### 7.1 创建索引

```cypher
-- 角色名索引 (唯一)
CREATE CONSTRAINT character_name IF NOT EXISTS
FOR (c:Character) REQUIRE c.name IS UNIQUE;

-- 组织名索引
CREATE CONSTRAINT org_name IF NOT EXISTS
FOR (o:Organization) REQUIRE o.name IS UNIQUE;

-- 事件名索引
CREATE INDEX event_name IF NOT EXISTS
FOR (e:Event) ON (e.name);

-- 全文搜索索引 (可选)
CREATE FULLTEXT INDEX character_fulltext IF NOT EXISTS
FOR (c:Character) ON EACH [c.name, c.aliases, c.description];
```

---

## 8. 数据维护

### 8.1 关系自动提取 (Phase 2)

```python
def extract_relations_from_chunk(chunk_text: str) -> List[Tuple[str, str, str]]:
    """
    从对话文本中自动提取关系 (简化版)

    Returns:
        [(entity1, relation, entity2), ...]
    """
    relations = []

    # 规则1: 同一场景出现的角色可能有交互
    characters = extract_characters(chunk_text)
    for i, char1 in enumerate(characters):
        for char2 in characters[i+1:]:
            relations.append((char1, "INTERACTS_WITH", char2))

    # 规则2: 特定关键词触发
    if "朋友" in chunk_text or "伙伴" in chunk_text:
        # 提取主语和宾语...
        pass

    return relations
```

### 8.2 增量更新

```python
def update_graph_from_new_data(new_chunks: List[Chunk]):
    """
    当有新数据时更新图

    Steps:
    1. 提取新角色 → 创建 Character 节点
    2. 提取新关系 → 创建 Relationship
    3. 创建 Chunk 节点并连接
    """
    pass
```

---

## 9. 验证检查清单

### 9.1 Schema 完整性

- [ ] 所有主要角色已创建
- [ ] 所有组织已创建
- [ ] 核心关系已建立
- [ ] 索引已创建

### 9.2 查询测试

```cypher
-- 测试1: 查询恰斯卡的所有关系
MATCH (c:Character {name: '恰斯卡'})-[r]-(other)
RETURN c.name, type(r), other.name;

-- 测试2: 查询花羽会成员
MATCH (c:Character)-[:MEMBER_OF]->(o:Organization {name: '花羽会'})
RETURN c.name, c.title;

-- 测试3: 查询基尼奇和阿尤的关系
MATCH path = (a:Character {name: '基尼奇'})-[*..2]-(b:Character {name: '阿尤'})
RETURN path;
```

### 9.3 与 graph_search 集成测试

```python
searcher = GraphSearcher()

# 测试1: 查询所有关系
result = searcher.search(entity="恰斯卡")
assert len(result["entities"]) > 0

# 测试2: 查询特定关系
result = searcher.search(entity="基尼奇", relation="PARTNER_OF")
assert any(e["target"] == "阿尤" for e in result["entities"])
```

---

## 附录: 关系类型速查表

| 关系类型 | 方向 | 说明 | 示例 |
|----------|------|------|------|
| FRIEND_OF | 双向 | 朋友关系 | 恰斯卡 ↔ 卡齐娜 |
| ENEMY_OF | 双向 | 敌对关系 | - |
| PARTNER_OF | 双向 | 伙伴关系 | 基尼奇 ↔ 阿尤 |
| MEMBER_OF | 单向 | 组织成员 | 恰斯卡 → 花羽会 |
| LEADER_OF | 单向 | 领导组织 | 恰斯卡 → 花羽会 |
| PARTICIPATED_IN | 单向 | 参与事件 | 旅行者 → 竞技场试炼 |
| OCCURRED_AT | 单向 | 事件地点 | 竞技场试炼 → 竞技场 |
| CONTAINS | 单向 | 包含文本 | 事件 → Chunk |
| NEXT | 单向 | 时序关系 | Chunk1 → Chunk2 |
