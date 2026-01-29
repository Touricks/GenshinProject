# 评测数据集

## 目录结构

```
evaluation/
├── README.md                 # 本文件 - 评测集说明
├── factual_qa.json          # 事实查询测试集
├── relation_qa.json         # 关系查询测试集
├── event_tracking.json      # 事件追踪测试集
├── multi_turn.json          # 多轮对话测试集
└── results/                 # 评测结果存放目录
    └── .gitkeep
```

## 数据格式规范

所有测试集使用 JSON 格式，便于自动化评测脚本读取。

### 单轮问答格式 (factual_qa.json, relation_qa.json, event_tracking.json)

```json
{
  "version": "1.0",
  "description": "事实查询测试集",
  "created_at": "2026-01-21",
  "items": [
    {
      "id": "fact_001",
      "category": "character",
      "difficulty": "easy",
      "question": "伊法的职业是什么？",
      "expected_answer": "医生",
      "source": {
        "file": "Data/1600/chapter0_dialogue.txt",
        "line_range": [34, 36]
      },
      "keywords": ["伊法", "医生", "花羽会"],
      "notes": "直接从对话中可获取"
    }
  ]
}
```

### 多轮对话格式 (multi_turn.json)

```json
{
  "version": "1.0",
  "description": "多轮对话测试集",
  "items": [
    {
      "id": "mt_001",
      "scenario": "角色信息追问",
      "turns": [
        {
          "turn": 1,
          "user": "恰斯卡是谁？",
          "expected_points": ["花羽会成员", "巡逻职责"]
        },
        {
          "turn": 2,
          "user": "她救了谁？",
          "expected_points": ["绒翼龙", "被秘源机兵袭击"],
          "requires_context": true
        },
        {
          "turn": 3,
          "user": "那些机兵是什么来历？",
          "expected_points": ["秘源机兵", "古怪机关"],
          "requires_context": true
        }
      ]
    }
  ]
}
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 唯一标识符，格式：`{类型}_{序号}` |
| category | string | 是 | 类别：character/location/event/relation/item |
| difficulty | string | 是 | 难度：easy/medium/hard |
| question | string | 是 | 测试问题 |
| expected_answer | string | 是 | 标准答案（简洁形式） |
| source | object | 是 | 答案来源定位 |
| keywords | array | 否 | 答案中应包含的关键词，用于自动评分 |
| notes | string | 否 | 标注说明 |
| requires_context | bool | 否 | 是否依赖上文（多轮对话专用） |

## 评测类别

### 1. 事实查询 (factual_qa.json)
- **目标数量**: 20 条
- **覆盖范围**: 角色属性、地点描述、物品信息
- **示例**: "派蒙第一次见到伊法是在哪里？"

### 2. 关系查询 (relation_qa.json)
- **目标数量**: 20 条
- **覆盖范围**: 人物关系、组织归属、地点关联
- **示例**: "恰斯卡属于哪个部族？"

### 3. 事件追踪 (event_tracking.json)
- **目标数量**: 15 条
- **覆盖范围**: 事件经过、因果关系、时间线
- **示例**: "秘源机兵袭击事件的经过是什么？"

### 4. 多轮对话 (multi_turn.json)
- **目标数量**: 10 组（每组 3-5 轮）
- **覆盖范围**: 指代消解、上下文记忆、话题延续
- **示例**: "她后来怎么样了？"（需正确关联上文角色）

## 评分标准

### 自动评分（基于 keywords）
- 完全匹配：所有关键词出现 → 1.0
- 部分匹配：部分关键词出现 → 匹配比例
- 无匹配：0.0

### 人工评分（1-5 分）
| 分数 | 标准 |
|------|------|
| 5 | 完全正确，信息完整 |
| 4 | 基本正确，有minor遗漏 |
| 3 | 部分正确，有明显遗漏 |
| 2 | 方向正确但关键信息错误 |
| 1 | 完全错误或无关 |

## 构建指南

1. 从 `Data/` 随机抽取章节
2. 阅读原文，编写问题
3. 标注标准答案和来源
4. 添加评分关键词
5. 交叉验证（另一人检查）
