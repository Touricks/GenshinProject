# Extraction Evaluation Datasets

> **Version**: 2.0
> **Created**: 2026-01-29
> **Purpose**: Benchmark vector database and graph database extraction pipelines

## Philosophy: Constraint-Based Testing

传统的精确匹配测试不适用于启发式抽取系统，原因：

1. **多种正确答案** - "恰斯卡和伊涅芙的关系"可以是 KNOWS、FRIEND_OF、HELPED 等
2. **领域专家也不确定** - 难以预测一个chunk应该抽取出多少实体/关系
3. **抽取粒度因系统而异** - 不同算法对"事件"的定义可能不同

**解决方案：测试约束和不变量，而非精确匹配**

```
传统测试：  expected_entities == extracted_entities  ❌
约束测试：  "伊法" in extracted_entities             ✓
           len(extracted_entities) >= 3             ✓
           no_duplicates(extracted_entities)        ✓
```

## Directory Structure

```
evaluation/extraction/
├── README.md                    # This file
├── chunking_eval.json           # 30 cases - 确定性高，精确测试
├── metadata_eval.json           # 40 cases - 确定性高，精确测试
├── entity_eval.json             # 25 cases - 约束测试
├── relationship_eval.json       # 20 cases - 约束测试
└── resolution_eval.json         # 15 cases - 约束测试
```

## Evaluation Layers

| Layer | 确定性 | 测试方式 | 示例 |
|-------|--------|----------|------|
| **Parsing** | 高 | 精确匹配 | `角色：对话` → 必须提取"角色" |
| **Entity** | 中 | 约束测试 | must_extract / should_extract |
| **Relationship** | 低 | 存在性测试 | must_relate（不检查类型） |
| **Property** | 很低 | 可选加分 | may_have_property |

## Constraint Types

### Entity Constraints

```json
{
  "constraints": {
    "must_extract": ["伊法", "恰斯卡"],      // 必须提取（缺失扣分）
    "should_extract": ["咔库库"],            // 应该提取（缺失不扣分）
    "may_extract": ["花羽会"],               // 可以提取（提取加分）
    "must_not_extract": ["玛薇卡"],          // 不应提取（防幻觉）
    "min_entity_count": 2,                   // 最少数量
    "entity_count_range": [2, 5]             // 数量范围
  }
}
```

### Relationship Constraints

```json
{
  "constraints": {
    "must_relate": [                          // 必须存在关系
      {"source": "咔库库", "target": "伊法"}
    ],
    "acceptable_types": ["WORKS_WITH", "ASSISTS"],  // 可接受的类型
    "must_not_relate": [                      // 不应存在的关系
      {"source": "派蒙", "target": "花羽会", "type": "MEMBER_OF"}
    ]
  }
}
```

### Resolution Constraints

```json
{
  "constraints": {
    "must_unify": ["杜麦尼", "旅行者", "玩家"],  // 必须合并为同一实体
    "must_not_unify": ["伊葵", "希诺宁"],        // 必须保持独立
    "result_entity_count": 1,                    // 结果实体数
    "no_duplicate_characters": true              // 不允许重复
  }
}
```

## Dataset Summaries

### 1. chunking_eval.json (Vector DB) - 精确测试

| Category | Count | 确定性 |
|----------|-------|--------|
| scene_boundary | 12 | 高 - `##` 和 `---` 明确 |
| choice_detection | 5 | 高 - `## 选项` 明确 |
| size_constraint | 5 | 高 - 字符数可计算 |
| context_preservation | 8 | 中 |

### 2. metadata_eval.json (Vector DB) - 精确测试

| Category | Count | 确定性 |
|----------|-------|--------|
| character_extraction | 18 | 高 - 格式明确 |
| task_info | 5 | 高 - 头部格式固定 |
| event_order | 5 | 高 - 可计算 |
| choice_detection | 5 | 高 |
| scene_name | 7 | 高 |

### 3. entity_eval.json (Graph DB) - 约束测试

| Layer | Count | 测试方式 |
|-------|-------|----------|
| parsing | 5 | must_extract |
| entity | 15 | must/should/may_extract |
| property | 3 | may_have_property |
| constraint | 2 | 整章/增量约束 |

### 4. relationship_eval.json (Graph DB) - 约束测试

| Layer | Count | 测试方式 |
|-------|-------|----------|
| parsing | 1 | 同场景必然认识 |
| explicit | 10 | 明确陈述的关系 |
| inferred | 5 | 推断的关系 |
| negative | 2 | 防幻觉 |
| constraint | 2 | 整章/增量约束 |

### 5. resolution_eval.json (Graph DB) - 约束测试

| Category | Count | 测试方式 |
|----------|-------|----------|
| alias_unification | 5 | must_unify |
| disambiguation | 1 | must_not_unify |
| deduplication | 3 | no_duplicates |
| cross_reference | 2 | 古名传承 |
| incremental | 2 | 增量去重 |
| constraint | 1 | 全章约束 |

## Scoring Strategy

### 分层评分

```python
def calculate_score(results):
    # Parsing层: 严格评分
    parsing_score = strict_match(results.parsing)  # 0 or 1

    # Entity层: 约束评分
    entity_score = (
        must_extract_score * 0.6 +      # 必须项权重高
        should_extract_score * 0.3 +    # 应该项权重中
        may_extract_score * 0.1         # 可选项权重低
    )

    # Relationship层: 存在性评分
    relationship_score = (
        must_relate_satisfied +
        negative_constraints_satisfied   # 防幻觉很重要
    )

    # 总分 = 加权平均
    return parsing_score * 0.3 + entity_score * 0.4 + relationship_score * 0.3
```

### 基线对比

```python
def test_extraction_quality():
    baseline_score = 0.72  # 上一版本的分数
    current_score = evaluate(new_extractor)

    # 不要求达到绝对指标，只要求不退步
    assert current_score >= baseline_score - 0.02
```

## Usage

### 加载评估数据

```python
import json
from pathlib import Path

eval_dir = Path("evaluation/extraction")

# 加载实体评估
with open(eval_dir / "entity_eval.json") as f:
    entity_data = json.load(f)

# 遍历测试用例
for case in entity_data["items"]:
    constraints = case["constraints"]

    # 执行抽取
    extracted = extractor.extract(case["input"]["text"])

    # 检查约束
    for must in constraints.get("must_extract", []):
        assert must in extracted, f"Missing required entity: {must}"
```

### 运行测试

```bash
# 运行所有抽取测试
pytest tests/extraction/ -v

# 只运行parsing层测试（确定性高）
pytest tests/extraction/ -v -m parsing

# 运行约束测试
pytest tests/extraction/ -v -m constraint
```

## Key Alias Mappings

| Canonical | Aliases |
|-----------|---------|
| 旅行者 | 杜麦尼, Traveler, 玩家 |
| 派蒙 | 白色飞行物, 飞行高手 |
| 伊涅芙 | ？？？, 机关人偶, 信使, 女仆机器人 |
| 咔库库 | 学舌怪怪龙 |
| 茜特菈莉 | 黑曜石奶奶 |

## Incremental Testing

增量填充数据库时的约束：

```json
{
  "precondition": {
    "existing_entities": ["恰斯卡", "派蒙", "伊法"]
  },
  "constraints": {
    "must_link_to_existing": ["恰斯卡", "派蒙"],
    "must_not_create_duplicate": true,
    "should_add_new": ["希诺宁"]
  }
}
```

关键不变量：
- **不重复**: 已有实体不应被重新创建
- **链接**: 新内容中提到的已有实体应链接到现有节点
- **别名更新**: 当正式名称出现时，临时占位符应被更新

## Contributing

添加新测试用例时：
1. 明确 layer (parsing/entity/relationship/property)
2. 使用约束而非精确匹配
3. 添加 notes 说明边界情况
4. 考虑防幻觉的负面约束
