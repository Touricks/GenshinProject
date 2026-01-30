"""
向量数据库工具：search_memory - 检索故事原文和对话。

此工具查询 Qdrant 向量数据库获取故事内容。
这是**唯一**返回故事原文的工具。
"""

from typing import Optional

from ..ingestion.indexer import VectorIndexer
from ..ingestion.embedder import EmbeddingGenerator


# 模块级单例，避免每次调用时重新加载模型
_embedder: Optional[EmbeddingGenerator] = None
_indexer: Optional[VectorIndexer] = None


def _get_embedder() -> EmbeddingGenerator:
    """获取或创建嵌入生成器单例。"""
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingGenerator()
    return _embedder


def _get_indexer() -> VectorIndexer:
    """获取或创建向量索引器单例。"""
    global _indexer
    if _indexer is None:
        _indexer = VectorIndexer()
    return _indexer


def search_memory(
    query: str,
    characters: Optional[str] = None,
    sort_by: str = "relevance",
    limit: int = 5,
) -> str:
    """
    搜索故事原文，获取特定剧情细节、对话或事件描述。

    这是**唯一**返回故事原文（文本片段）的工具。
    使用场景：
    - "玛薇卡说了什么？" (query="玛薇卡的发言")
    - "描述竞技场的战斗" (query="竞技场战斗")
    - "少女和旅行者的对话" (query="少女 旅行者 对话", characters="少女")

    参数：
        query: 描述要搜索的事件、对话或场景的自然语言查询。
        characters: 可选的角色名过滤器。只返回提及此角色的内容。
        sort_by: 结果排序方式。
                 - "relevance"（默认）：按语义相关度排序。
                 - "time"：按章节和事件顺序排序。
                   当询问事件序列时使用 "time"。
        limit: 返回结果的最大数量（默认：5，最大：20）。
               更大的值提供更多上下文，但可能较慢。

    返回：
        带有章节/来源引用的故事文本片段。
        每个片段包含实际的对话或叙述内容。
    """
    embedder = _get_embedder()
    indexer = _get_indexer()

    # 生成查询嵌入向量
    query_vector = embedder.embed_single(query)

    # 构建过滤条件
    filter_conditions = None
    if characters:
        filter_conditions = {"characters": characters}

    # 搜索向量数据库
    results = indexer.search(
        query_vector=query_vector,
        limit=min(limit, 20),  # 限制最大20条以避免结果过多
        filter_conditions=filter_conditions,
        sort_by=sort_by,
    )

    if not results:
        msg = f"未找到与查询 '{query}' 相关的故事内容"
        if characters:
            msg += f"（已过滤角色：{characters}）"
        msg += "\n\n建议：\n"
        msg += "- 尝试更宽泛或不同的查询词。\n"
        msg += "- 移除角色过滤器以搜索所有内容。\n"
        msg += "- 使用 lookup_knowledge 验证角色名是否正确。"
        return msg

    # 格式化结果，包含引用
    lines = [f"## 故事内容：\"{query}\""]
    if characters:
        lines.append(f"（已过滤角色：{characters}）")
    lines.append(f"（排序方式：{sort_by}）")
    lines.append("")

    for i, result in enumerate(results, 1):
        payload = result["payload"]
        text = payload.get("text", "")
        chapter = payload.get("chapter_number", "?")
        task_id = payload.get("task_id", "未知")
        event_order = payload.get("event_order", 0)
        score = result.get("score", 0)

        lines.append(f"### 结果 {i}")
        lines.append(f"**来源**: 第 {chapter} 章，任务: {task_id}，事件 #{event_order}")
        if sort_by == "relevance":
            lines.append(f"**相关度**: {score:.3f}")
        lines.append("")
        lines.append(text)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
