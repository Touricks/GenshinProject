"""
向量数据库工具：search_memory - 检索故事原文和对话。

此工具查询 Qdrant 向量数据库获取故事内容。
这是**唯一**返回故事原文的工具。
"""

import logging
from typing import List, Optional

from ..ingestion.indexer import VectorIndexer
from ..ingestion.embedder import EmbeddingGenerator
from ..graph.searcher import GraphSearcher
from ..config.aliases import CHARACTER_ALIASES

logger = logging.getLogger(__name__)


# 模块级 GraphSearcher 单例，用于别名解析
_graph_searcher: Optional[GraphSearcher] = None


def _get_graph_searcher() -> GraphSearcher:
    """获取或创建 GraphSearcher 单例用于别名解析。"""
    global _graph_searcher
    if _graph_searcher is None:
        _graph_searcher = GraphSearcher()
    return _graph_searcher


def _resolve_character_alias(name: str) -> str:
    """
    解析角色别名为规范名称。

    解析策略（按优先级）：
    1. 手动别名映射表（修复图数据库缺失的关联）
    2. Neo4j fulltext index（标准别名解析）
    3. 原名返回（fallback）

    Args:
        name: 角色名或别名

    Returns:
        解析后的规范名称，如果解析失败则返回原名
    """
    # 1. 先检查手动别名映射表（来自 src/config/aliases.py）
    if name in CHARACTER_ALIASES:
        canonical = CHARACTER_ALIASES[name]
        logger.info(f"[Alias] Manual mapping '{name}' -> '{canonical}'")
        return canonical

    # 2. 尝试 Neo4j fulltext index
    try:
        searcher = _get_graph_searcher()
        canonical = searcher._resolve_canonical_name(name)
        if canonical != name:
            logger.info(f"[Alias] Graph resolved '{name}' -> '{canonical}'")
        return canonical
    except Exception as e:
        logger.warning(f"[Alias] Failed to resolve '{name}': {e}")
        return name


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


def _deduplicate_results(results: List[dict]) -> List[dict]:
    """基于 (task_id, event_order) 去重，保留 score 最高的 chunk。

    同一个 event 可能被分成多个 chunk（不同 chunk_order），
    这会导致搜索结果中出现重复内容。此函数保留每个唯一事件的最高分 chunk。

    Args:
        results: 按 score 降序排列的搜索结果列表。

    Returns:
        去重后的结果列表，保持原顺序。
    """
    seen = {}  # key: (task_id, event_order), value: result
    for result in results:
        payload = result.get("payload", {})
        key = (payload.get("task_id"), payload.get("event_order"))
        if key not in seen:
            seen[key] = result
        # results 已按 score 降序，首次出现的即最高分
    return list(seen.values())


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
    logger.info(
        f"[Qdrant] search_memory: query={query[:50]}{'...' if len(query) > 50 else ''}, "
        f"characters={characters}, sort_by={sort_by}, limit={limit}"
    )

    embedder = _get_embedder()
    indexer = _get_indexer()

    # 生成查询嵌入向量
    query_vector = embedder.embed_single(query)

    # 构建过滤条件（支持别名解析）
    filter_conditions = None
    resolved_characters = None
    if characters:
        # 解析角色别名为规范名称（如 "木偶" -> "桑多涅"）
        resolved_characters = _resolve_character_alias(characters)
        filter_conditions = {"characters": resolved_characters}

    # 启发式扩展搜索：如果去重后不足 limit，则翻倍搜索
    # 这解决了同一 event 多个 chunk 导致重复结果的问题
    target_limit = min(limit, 20)
    max_fetch = target_limit * 8  # 最大搜索量 = limit * 8
    fetch_limit = target_limit
    unique_results = []

    while fetch_limit <= max_fetch:
        raw_results = indexer.search(
            query_vector=query_vector,
            limit=fetch_limit,
            filter_conditions=filter_conditions,
            sort_by=sort_by,
        )
        unique_results = _deduplicate_results(raw_results)

        logger.debug(
            f"[Qdrant] fetch_limit={fetch_limit}, raw={len(raw_results)}, "
            f"unique={len(unique_results)}"
        )

        if len(unique_results) >= target_limit:
            break  # 已找到足够的不同 chunk

        fetch_limit *= 2  # 翻倍重试

    # 降级策略：如果角色过滤返回 0 结果，尝试不使用过滤但将角色名加入查询
    # 这解决了 characters 元数据只包含说话者（不包含被提及角色）的问题
    fallback_used = False
    if not unique_results and filter_conditions and resolved_characters:
        logger.info(
            f"[Qdrant] Character filter returned 0 results, "
            f"falling back to query with character name"
        )
        # 将角色名加入查询重新搜索
        augmented_query = f"{resolved_characters} {query}"
        augmented_vector = embedder.embed_single(augmented_query)

        fetch_limit = target_limit
        while fetch_limit <= max_fetch:
            raw_results = indexer.search(
                query_vector=augmented_vector,
                limit=fetch_limit,
                filter_conditions=None,  # 不使用角色过滤
                sort_by=sort_by,
            )
            unique_results = _deduplicate_results(raw_results)

            logger.debug(
                f"[Qdrant] fallback fetch_limit={fetch_limit}, raw={len(raw_results)}, "
                f"unique={len(unique_results)}"
            )

            if len(unique_results) >= target_limit:
                break
            fetch_limit *= 2

        fallback_used = True

    results = unique_results[:target_limit]

    logger.debug(
        f"[Qdrant] search_memory result: {len(results)} unique chunks "
        f"(target={target_limit})"
    )

    if not results:
        msg = f"未找到与查询 '{query}' 相关的故事内容"
        if characters:
            if resolved_characters and resolved_characters != characters:
                msg += f"（已过滤角色：{characters} → {resolved_characters}）"
            else:
                msg += f"（已过滤角色：{characters}）"
        msg += "\n\n建议：\n"
        msg += "- 尝试更宽泛或不同的查询词。\n"
        msg += "- 移除角色过滤器以搜索所有内容。\n"
        msg += "- 使用 lookup_knowledge 验证角色名是否正确。"
        return msg

    # 格式化结果，包含引用
    lines = [f"## 故事内容：\"{query}\""]
    if characters:
        if fallback_used:
            lines.append(f"（角色过滤无结果，已改用语义搜索：{resolved_characters}）")
        elif resolved_characters and resolved_characters != characters:
            lines.append(f"（已过滤角色：{characters} → {resolved_characters}）")
        else:
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
