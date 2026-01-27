这是一个为您整合的完整技术方案文档。您可以将其保存为 Markdown 文件或直接用于项目技术文档。

---

# 叙事类私有数据集构建方案：基于 LlamaIndex Property Graph

**目标场景**：RPG 剧本/小说文本（含大量对话、心声、插叙及别名）
**数据原型**：`chapter1_dialogue.txt` (及同类 200+ 文件)

## 1. 原型数据分析

基于您提供的 `chapter1_dialogue.txt`，该数据集具有以下鲜明特征，需针对性处理：

* 
**多层叙事结构**：文本中包含“现实层”（如奈芙尔进行仪式）和“记忆层/嵌套层”（如通过仪式观看雷利尔的过去）。若不加区分，会导致图谱时空错乱 。


* 
**高密度的潜台词**：大量关键剧情隐藏在 `（...）` 包裹的内心独白中。例如玩家怀疑环境真实性 `玩家：（奇怪，我记得...）`，或奈芙尔的推理 `奈芙尔：（没有署名…看来留言人跟雷利尔很熟...）` 。


* 
**复杂的指代体系**：同一人物混用代号与本名（如 `「木偶」` / `桑多涅`，`雷利尔` / `猎月人`），且存在阵营流动性 。


* **非线性时间线**：包含回忆杀（如雷利尔与索琳蒂丝的往事）和预言。

## 2. 图谱 Schema 设计

为了适配上述特征，我们采用 **Property Graph (属性图)** 模型，定义如下 Schema：

### 2.1 实体定义 (Entities)

| 实体类型 | 说明 | 示例 (来自原文) |
| --- | --- | --- |
| **Character** | 角色 | 玩家, 派蒙, 「木偶」, 桑多涅, 雷利尔, 索琳蒂丝 

 |
| **Location** | 地点 | 那夏镇, 试验设计局, 坎瑞亚, 烤肉店 

 |
| **Event** | 事件/仪式 | 祈月之夜, 猎月人战斗, 奈芙尔的仪式 

 |
| **Concept** | 设定/道具 | 月髓, 寻宝罗盘, 喷气背包 

 |

### 2.2 关系定义 (Relations)

| 关系类型 | 说明 | 适用场景 |
| --- | --- | --- |
| **SPEAKS_TO** | 对话 | 两人之间的显性交流。 |
| **THINKS** | **心声/独白** | **关键**：提取括号 `（）` 内的内容，反映角色真实意图。 |
| **OBSERVES_MEMORY_OF** | **记忆观测** | **关键**：用于嵌套叙事，如奈芙尔观看雷利尔的记忆。 |
| **IS_ALIAS_OF** | 别名指向 | 解决 `猎月人` = `雷利尔` 的问题。 |
| **CONCEALS_IDENTITY_FROM** | 隐瞒/欺骗 | 专门用于类似雷利尔隐瞒未婚妻的情节。 |
| **PLOTS_AGAINST** | 敌对/谋划 | 比简单的“讨厌”更具叙事张力。 |

---

## 3. 定制化 Prompt 模板 (v2.0)

此 Prompt 经过微调，专门用于解决“嵌套叙事”和“心声提取”问题。

```python
NARRATIVE_KG_PROMPT = """
您是一位精通叙事结构和情报分析的专家。您的任务是从以下剧本/小说文本中提取结构化的知识图谱三元组。

文本片段如下：
---------------------
{text}
---------------------

请严格遵守以下提取规则：

1. **实体识别 (Entities)**：
   - 提取主要 **角色 (Character)**、**地点 (Location)**、**关键事件 (Event)**。
   - **别名对齐**：如果文中出现同一人物的别名（如“雷利尔”和“猎月人”），请提取 (别名, IS_ALIAS_OF, 正式名) 关系。

2. **关系提取 (Relations) - 必须精准区分语境**：
   - **THINKS (心声)**：内容在全角括号 `（` 或半角括号 `(` 内，这是角色的内心独白。
     - 格式：(角色, THINKS, "摘要心声内容")
     - *示例*：原文 `玩家：（奇怪，我记得...）` -> 提取 `(玩家, THINKS, "质疑环境真实性")`
   
   - **OBSERVES_MEMORY_OF (记忆/仪式观测)**：
     - 当文本描述一个角色正在通过仪式、梦境或观看记录来观察另一个角色的过去时。
     - *示例*：原文 `奈芙尔：（...雷利尔成为猎月人之前...）` -> 提取 `(奈芙尔, OBSERVES_MEMORY_OF, 雷利尔)`
     - 注意：此时被观察的场景（如雷利尔和未婚妻的对话）属于“MEMORY”层级，不应被视为奈芙尔亲身参与。

   - **SPEAKS_TO (对话)**：公开的语言交流。
   
   - **CONCEALS / REVEALS (信息流)**：
     - 角色刻意隐瞒身份或秘密。
     - *示例*：`雷利尔` 隐瞒 `索琳蒂丝` 关于他工作的真相。

3. **格式要求**：
   - 输出格式必须是 JSON 列表，每一项包含 "subject", "relation", "object"。
   - 忽略无意义的寒暄，只保留推动剧情或揭示设定的信息。

请按以下 JSON 格式输出提取结果：
[
  {{"subject": "实体A", "relation": "关系", "object": "实体B"}},
  ...
]
"""

```

---

## 4. LlamaIndex 实现代码 (Python)

使用 `PropertyGraphIndex` 和自定义提取器构建索引。

```python
import os
from llama_index.core import SimpleDirectoryReader, PropertyGraphIndex
from llama_index.core.indices.property_graph import SimpleLLMPathExtractor
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.llms.openai import OpenAI # 或其他 LLM

# 1. 准备数据与 Metadata 处理
# 建议在读取时注入章节信息，便于后续按章节筛选
def get_file_metadata(file_path):
    file_name = os.path.basename(file_path)
    # 简单的文件名解析逻辑，根据您的实际文件名修改
    return {"file_name": file_name, "category": "narrative"}

documents = SimpleDirectoryReader(
    "./your_data_folder", 
    file_metadata=get_file_metadata
).load_data()

# 2. 配置自定义提取器
# 注入我们定义的 NARRATIVE_KG_PROMPT
kg_extractor = SimpleLLMPathExtractor(
    llm=OpenAI(model="gpt-4o", temperature=0.1), # 建议使用强指令遵循模型
    extract_prompt=NARRATIVE_KG_PROMPT,
    max_paths_per_chunk=15, # 剧本信息密度高，调高上限
    strict=True
)

# 3. 构建属性图索引 (Graph + Vector)
index = PropertyGraphIndex.from_documents(
    documents,
    kg_extractors=[kg_extractor],
    property_graph_store=SimpleGraphStore(), # 生产环境建议替换为 Neo4jGraphStore
    vector_store=None, # LlamaIndex 默认会为节点创建向量索引
    show_progress=True
)

# 4. 保存索引（持久化）
index.storage_context.persist(persist_dir="./storage_graph")

print("构建完成。现在可以进行混合检索了。")

```

## 5. 检索与维护建议

### 检索策略 (Retrieval)

针对剧情类问题，建议使用 **混合检索 (Hybrid Retrieval)**：

```python
retriever = index.as_retriever(
    include_text=True,  # 返回关联的原始文本块
    vector_store_query_mode="hybrid", # 同时使用关键词匹配和向量相似度
    similarity_top_k=5
)

# 测试查询：这种问题只有通过图谱推理+向量才能回答准确
response = retriever.retrieve("奈芙尔通过仪式发现了雷利尔的什么秘密？")

```

### 数据维护 (Maintenance)

* **章节隔离**：由于您有 200 个文件，建议在 Metadata 中加入 `chapter_index`。当检索“第一章剧情”时，可使用 Metadata Filter 避免后续章节剧透。
* **别名修正**：定期运行 `index.property_graph_store.get_triplets(entity_name="某别名")`，检查是否需要手动合并节点（例如将漏网的“那个黑商”手动指向“多莉”）。