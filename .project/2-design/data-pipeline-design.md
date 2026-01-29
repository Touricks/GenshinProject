# Data Pipeline Design

> **状态**: Draft
> **创建时间**: 2026-01-29
> **关联文档**: techstack-plan.md, ADR-006-final-tool-design.md

---

## 1. 数据源分析

### 1.1 文件结构

```
Data/
├── 1500/                     # 任务ID (须弥系列)
│   ├── chapter0_dialogue.txt
│   ├── chapter1_dialogue.txt
│   └── chapter2_dialogue.txt
├── 1600/                     # 任务ID (纳塔系列)
│   ├── chapter0_dialogue.txt
│   ├── chapter1_dialogue.txt
│   └── chapter2_dialogue.txt
├── 1601/
├── 1602/
├── ...
└── 1608/
```

### 1.2 文件格式

```markdown
# 任务名称 - 第X章：章节名
# 系列名称（如：空月之歌 第X幕）
# 来源：URL

## 剧情简介
简介内容...

---

## 场景/剧情段落标题

角色名：对话内容
角色名：对话内容
玩家：选项或对话内容

## 选项
- 选项1
- 选项2

玩家：选项1

角色名：回应...

---

## 下一个场景
...
```

### 1.3 数据统计

| 指标 | 估算值 |
|------|--------|
| 任务数量 | ~15-20 个 |
| 章节总数 | ~50-60 个 |
| 预估 Chunk 数 | 5,000-10,000 |
| 预估向量存储 | ~30 MB |

---

## 2. Chunking 策略

### 2.1 策略选型

| 策略 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| Fixed-size | 简单、均匀 | 切断对话上下文 | ❌ 不适用 |
| Sentence | 保持句子完整 | 对话上下文不完整 | ❌ 不适用 |
| **Semantic (Scene-based)** | 保持场景完整 | 可能过长 | ✅ 选用 |
| Paragraph | 简单 | 场景可能被切断 | 备选 |

**选择: Scene-based Semantic Chunking**

### 2.2 Chunking 规则

```python
# 主要分隔符 (按优先级)
SCENE_DELIMITERS = [
    r'^## .+',           # 场景标题
    r'^---$',            # 水平分割线
    r'^## 选项',         # 选项标记
    r'^## Scenario \d+', # 分支场景
]

# Chunk 大小限制
MAX_CHUNK_SIZE = 1500  # 字符
MIN_CHUNK_SIZE = 200   # 字符
OVERLAP_SIZE = 100     # 重叠字符 (用于上下文连续性)
```

### 2.3 Chunking 伪代码

```python
def chunk_dialogue_file(content: str, metadata: dict) -> List[Chunk]:
    """
    基于场景的语义分块

    Args:
        content: 文件内容
        metadata: 文件级元数据 (task_id, chapter, etc.)

    Returns:
        Chunk 列表
    """
    chunks = []

    # Step 1: 按场景分割
    scenes = split_by_scenes(content)

    for i, scene in enumerate(scenes):
        scene_name = extract_scene_name(scene)
        scene_content = clean_scene_content(scene)

        # Step 2: 如果场景过长，进一步分割
        if len(scene_content) > MAX_CHUNK_SIZE:
            sub_chunks = split_long_scene(scene_content)
        else:
            sub_chunks = [scene_content]

        # Step 3: 提取角色和创建 Chunk
        for j, sub_chunk in enumerate(sub_chunks):
            characters = extract_characters(sub_chunk)

            chunk = Chunk(
                text=sub_chunk,
                metadata={
                    **metadata,
                    "scene_name": scene_name,
                    "scene_order": i,
                    "chunk_order": j,
                    "characters": characters,
                }
            )
            chunks.append(chunk)

    return chunks
```

### 2.4 长场景处理

```python
def split_long_scene(scene_content: str) -> List[str]:
    """
    对超长场景进行二次分割

    策略:
    1. 优先按对话轮次分割 (5-10 轮为一个 chunk)
    2. 保持对话完整性 (不切断单个角色的发言)
    3. 添加重叠 (overlap) 保持上下文
    """
    dialogues = parse_dialogues(scene_content)

    chunks = []
    current_chunk = []
    current_size = 0

    for dialogue in dialogues:
        dialogue_size = len(dialogue)

        if current_size + dialogue_size > MAX_CHUNK_SIZE and current_chunk:
            # 保存当前 chunk
            chunks.append("\n".join(current_chunk))
            # 带 overlap 开始新 chunk
            overlap_start = max(0, len(current_chunk) - 2)
            current_chunk = current_chunk[overlap_start:]
            current_size = sum(len(d) for d in current_chunk)

        current_chunk.append(dialogue)
        current_size += dialogue_size

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks
```

---

## 3. Metadata Schema

### 3.1 Document-level Metadata (文件级)

```python
@dataclass
class DocumentMetadata:
    """从文件头提取的元数据"""
    task_id: str           # "1600", "1601", ...
    task_name: str         # "归途", "终北的夜行诗", ...
    chapter_number: int    # 0, 1, 2, ...
    chapter_name: str      # "墟火", "白夜降临", ...
    series_name: str       # "空月之歌 第X幕"
    source_url: str        # 原始来源 URL
    summary: str           # 剧情简介
```

### 3.2 Chunk-level Metadata (Chunk 级)

```python
@dataclass
class ChunkMetadata:
    """存入 Qdrant Payload 的元数据"""
    # === 继承自 Document ===
    task_id: str
    task_name: str
    chapter_number: int
    chapter_name: str
    series_name: str

    # === Chunk 特有 ===
    scene_name: str            # "与恰斯卡对话", "击败秘源机兵", ...
    scene_order: int           # 场景在章节中的顺序 (0, 1, 2, ...)
    chunk_order: int           # Chunk 在场景中的顺序 (通常为 0)
    event_order: int           # 全局事件顺序 = chapter_number * 1000 + scene_order * 10 + chunk_order
    characters: List[str]      # 该 Chunk 中出现的角色 ["恰斯卡", "派蒙", "玩家"]

    # === 可选 ===
    has_choice: bool           # 是否包含选项分支
    scenario_id: Optional[int] # 分支场景 ID (1, 2, 3)
```

### 3.3 Qdrant Payload 示例

```json
{
    "task_id": "1600",
    "task_name": "归途",
    "chapter_number": 0,
    "chapter_name": "墟火",
    "series_name": "空月之歌 序奏",
    "scene_name": "与恰斯卡对话",
    "scene_order": 1,
    "chunk_order": 0,
    "event_order": 10,
    "characters": ["恰斯卡", "派蒙", "玩家", "伊法", "咔库库"],
    "has_choice": false,
    "text": "伊法：…伤口已经处理完了。所以你是在哪发现的它？..."
}
```

---

## 4. 角色提取

### 4.1 角色识别规则

```python
def extract_characters(text: str) -> List[str]:
    """
    从对话文本中提取角色名

    规则:
    1. 匹配 "角色名：" 格式
    2. 过滤系统角色 ("？？？", "小机器人", etc.)
    3. 归一化角色名 ("玩家" → 保留, 不做实体链接)
    """
    pattern = r'^([^：\n]+)：'

    raw_characters = re.findall(pattern, text, re.MULTILINE)

    # 过滤和清洗
    SYSTEM_CHARS = {"？？？", "选项", "---"}
    characters = [c.strip() for c in raw_characters if c.strip() not in SYSTEM_CHARS]

    return list(set(characters))
```

### 4.2 核心角色列表 (用于 entity_filter)

```python
MAIN_CHARACTERS = [
    # 纳塔主要角色
    "恰斯卡", "卡齐娜", "玛拉妮", "基尼奇", "阿尤",
    "希诺宁", "伊法", "穆洛塔",
    # 旅行者
    "玩家", "派蒙", "旅行者",
    # 其他重要角色
    "咔库库", "阿赫玛尔", "赛塔蕾",
]
```

---

## 5. 数据处理流水线

### 5.1 Pipeline 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Data Ingestion Pipeline                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Data/                                                              │
│  └── {task_id}/                                                     │
│      └── chapter{N}_dialogue.txt                                    │
│                    │                                                │
│                    ▼                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 1: Document Loader                                     │   │
│  │  - 解析文件头 (任务名、章节名、系列名)                        │   │
│  │  - 提取剧情简介                                              │   │
│  │  - 创建 DocumentMetadata                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                    │                                                │
│                    ▼                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 2: Scene Chunker                                       │   │
│  │  - 按场景分割 (## 标记)                                       │   │
│  │  - 长场景二次分割                                            │   │
│  │  - 添加 overlap                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                    │                                                │
│                    ▼                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 3: Metadata Enricher                                   │   │
│  │  - 提取角色列表                                              │   │
│  │  - 计算 event_order                                          │   │
│  │  - 检测选项分支                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                    │                                                │
│                    ▼                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 4: Embedding Generator                                 │   │
│  │  - BGE-base-zh-v1.5                                          │   │
│  │  - Batch processing (batch_size=64)                          │   │
│  │  - MPS 加速                                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                    │                                                │
│                    ▼                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 5: Vector Storage                                      │   │
│  │  - Qdrant upsert                                             │   │
│  │  - Collection: genshin_story                                 │   │
│  │  - Payload: ChunkMetadata                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                    │                                                │
│                    ▼                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Step 6: Graph Builder (Optional - Phase 2)                  │   │
│  │  - 提取实体关系                                              │   │
│  │  - 写入 Neo4j                                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 代码结构

```
src/
├── ingestion/
│   ├── __init__.py
│   ├── loader.py           # DocumentLoader - 文件解析
│   ├── chunker.py          # SceneChunker - 场景分割
│   ├── enricher.py         # MetadataEnricher - 元数据提取
│   ├── embedder.py         # EmbeddingGenerator - 向量生成
│   └── indexer.py          # VectorIndexer - Qdrant 写入
├── models/
│   ├── __init__.py
│   ├── document.py         # DocumentMetadata dataclass
│   └── chunk.py            # Chunk, ChunkMetadata dataclasses
└── scripts/
    └── ingest.py           # CLI 入口: python -m scripts.ingest Data/
```

---

## 6. Qdrant Collection 配置

### 6.1 Collection Schema

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType

client = QdrantClient(url="http://localhost:6333")

# 创建 Collection
client.create_collection(
    collection_name="genshin_story",
    vectors_config=VectorParams(
        size=768,          # BGE-base-zh 维度
        distance=Distance.COSINE
    )
)

# 创建 Payload 索引 (用于过滤)
client.create_payload_index(
    collection_name="genshin_story",
    field_name="task_id",
    field_schema=PayloadSchemaType.KEYWORD
)
client.create_payload_index(
    collection_name="genshin_story",
    field_name="chapter_number",
    field_schema=PayloadSchemaType.INTEGER
)
client.create_payload_index(
    collection_name="genshin_story",
    field_name="characters",
    field_schema=PayloadSchemaType.KEYWORD  # Array of keywords
)
client.create_payload_index(
    collection_name="genshin_story",
    field_name="event_order",
    field_schema=PayloadSchemaType.INTEGER
)
```

### 6.2 Upsert 示例

```python
from qdrant_client.models import PointStruct

points = [
    PointStruct(
        id=hash(f"{chunk.metadata.task_id}_{chunk.metadata.event_order}"),
        vector=embedding,
        payload=chunk.metadata.to_dict()
    )
    for chunk, embedding in zip(chunks, embeddings)
]

client.upsert(collection_name="genshin_story", points=points)
```

---

## 7. 验证检查清单

### 7.1 数据质量检查

- [ ] 所有文件成功解析
- [ ] Chunk 大小在 200-1500 字符范围内
- [ ] 每个 Chunk 至少包含 1 个角色
- [ ] event_order 无重复

### 7.2 索引完整性检查

- [ ] Qdrant collection 创建成功
- [ ] 所有 Chunk 成功 upsert
- [ ] Payload 索引创建成功
- [ ] 简单查询测试通过

### 7.3 检索测试

```python
# 测试查询
results = client.search(
    collection_name="genshin_story",
    query_vector=embed("恰斯卡的性格"),
    limit=5
)

assert len(results) > 0
assert "恰斯卡" in results[0].payload.get("characters", [])
```

---

## 附录 A: 文件头解析正则

```python
HEADER_PATTERNS = {
    "task_chapter": r'^# (.+) - 第(\d+)章[：:](.+)$',
    "series": r'^# (.+第.+幕)$',
    "source": r'^# 来源[：:](.+)$',
    "summary_start": r'^## 剧情简介$',
}

def parse_header(content: str) -> DocumentMetadata:
    lines = content.split('\n')

    task_chapter_match = re.match(HEADER_PATTERNS["task_chapter"], lines[0])
    if task_chapter_match:
        task_name = task_chapter_match.group(1)
        chapter_number = int(task_chapter_match.group(2))
        chapter_name = task_chapter_match.group(3)

    # ... 继续解析其他字段
```
