"""
知识图谱工具：track_journey - 追踪实体的关系变化历程。

此工具从 Neo4j 知识图谱获取关系历史。
返回按时间排序的状态变化（非详细剧情）。
"""

from typing import Optional

from ..graph.searcher import GraphSearcher


def track_journey(entity: str, target: Optional[str] = None) -> str:
    """
    追踪角色的历程或关系状态变化时间线。

    使用场景：
    - "旅行者在纳塔的经历" (entity="旅行者")
    - "少女和努昂诺塔的关系是如何发展的？" (entity="少女", target="努昂诺塔")
    - "某角色的组织隶属变化历史" (entity="角色名")

    返回按时间排序的状态更新，不包含详细剧情。
    如需剧情细节，请在获取时间线后使用 search_memory。

    参数：
        entity: 要追踪的主要角色。
        target: 可选的特定角色，用于追踪与其的关系变化。

    返回：
        按章节排序的关系状态变化列表。
        如果未找到历史记录，返回建议使用 search_memory 的提示。
    """
    with GraphSearcher() as searcher:
        history = searcher.search_history(entity, target=target)

    if not history:
        msg = f"在知识图谱中未找到 '{entity}' 的时间历程"
        if target:
            msg += f"（与 '{target}' 的关系）"
        msg += "。\n\n"
        msg += "建议：\n"
        msg += f"- 使用 search_memory(query=\"{entity}"
        if target:
            msg += f" {target}"
        msg += "\", sort_by=\"time\") 按时间顺序搜索故事内容。"
        return msg

    # 格式化为时间线
    lines = [f"## 时间线：{entity}"]
    if target:
        lines.append(f"（与 {target} 的关系）")
    lines.append("")

    current_chapter = None
    for event in history:
        chapter = event.get("chapter", "未知")
        task_id = event.get("task_id", "")
        relation = event.get("relation", "RELATED_TO")
        event_target = event.get("target", "未知")
        evidence = event.get("evidence", "")

        # 按章节分组
        if chapter != current_chapter:
            if current_chapter is not None:
                lines.append("")
            lines.append(f"### 第 {chapter} 章")
            current_chapter = chapter

        # 格式化事件
        line = f"- [{relation}] → {event_target}"
        if task_id:
            line += f" (任务: {task_id})"
        lines.append(line)

        if evidence:
            # 截断证据以保持输出简洁
            evidence_short = evidence[:150] + "..." if len(evidence) > 150 else evidence
            lines.append(f"  > 证据: {evidence_short}")

    lines.append("")
    lines.append(f"共找到 {len(history)} 条关系事件。")
    lines.append("")
    lines.append("**提示**: 如需详细剧情内容，请使用 search_memory 搜索此时间线中的特定事件。")

    return "\n".join(lines)
