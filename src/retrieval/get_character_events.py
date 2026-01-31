"""
知识图谱工具：get_character_events - 获取角色的重大事件/转折点。

此工具查询 Neo4j 知识图谱中的 MajorEvent 节点。
解决"抽象查询 vs 具体叙事"的语义鸿沟问题。
"""

from typing import Optional

from ..graph.searcher import GraphSearcher


# Valid event types for validation
VALID_EVENT_TYPES = {
    "sacrifice",
    "transformation",
    "acquisition",
    "loss",
    "encounter",
    "conflict",
    "revelation",
    "milestone",
}

# Event type descriptions for user reference
EVENT_TYPE_DESCRIPTIONS = {
    "sacrifice": "牺牲 - 角色付出重大代价",
    "transformation": "转变 - 角色状态/形态改变",
    "acquisition": "获得 - 角色获得力量/物品",
    "loss": "失去 - 角色失去某物/某人",
    "encounter": "相遇 - 重要人物相遇",
    "conflict": "冲突 - 战斗/对抗",
    "revelation": "揭示 - 真相/秘密揭露",
    "milestone": "里程碑 - 重要转折点",
}


def get_character_events(
    entity: str,
    event_type: Optional[str] = None,
) -> str:
    """
    获取角色的重大事件和转折点。

    使用场景：
    - "少女经历了什么？" (entity="少女")
    - "少女是如何重回世界的？" (entity="少女", event_type=None 或 "milestone")
    - "谁牺牲了？发生了什么牺牲事件？" (event_type="sacrifice")
    - "旅行者获得了什么？" (entity="旅行者", event_type="acquisition")

    此工具解决"抽象查询 vs 具体叙事"的语义鸿沟：
    - 用户问："少女是如何重回世界的"
    - 数据库包含："献出身体"、"化作月光"、"权能转交"
    - 此工具返回这些具体事件，帮助回答抽象问题

    参数：
        entity: 角色名称。支持别名自动解析。
        event_type: 可选的事件类型过滤：
                    - sacrifice (牺牲)
                    - transformation (转变)
                    - acquisition (获得)
                    - loss (失去)
                    - encounter (相遇)
                    - conflict (冲突)
                    - revelation (揭示)
                    - milestone (里程碑)

    返回：
        包含角色重大事件的结构化文本，按章节排序。
        如果未找到事件，返回建议使用 search_memory 的提示。
    """
    # Validate event_type parameter
    if event_type and event_type not in VALID_EVENT_TYPES:
        valid_list = ", ".join(sorted(VALID_EVENT_TYPES))
        return (
            f"无效的事件类型 '{event_type}'。\n\n"
            f"有效类型：{valid_list}\n\n"
            "请使用有效的事件类型重试。"
        )

    with GraphSearcher() as searcher:
        events = searcher.get_major_events(entity, event_type=event_type, limit=20)

    if not events:
        msg = f"在知识图谱中未找到 '{entity}' 的重大事件"
        if event_type:
            type_desc = EVENT_TYPE_DESCRIPTIONS.get(event_type, event_type)
            msg += f"（类型：{type_desc}）"
        msg += "。\n\n"
        msg += "建议：\n"
        msg += f"1. 使用 track_journey(entity=\"{entity}\") 查看关系时间线\n"
        msg += f"2. 使用 search_memory(query=\"{entity}"
        if event_type:
            msg += f" {event_type}"
        msg += "\") 搜索相关对话内容"
        return msg

    # Format output as structured Markdown
    lines = [f"## 重大事件：{entity}"]

    if event_type:
        type_desc = EVENT_TYPE_DESCRIPTIONS.get(event_type, event_type)
        lines.append(f"(已过滤事件类型：{type_desc})")

    lines.append("")

    current_chapter = None
    for event in events:
        chapter = event.get("chapter", "未知")
        event_name = event.get("event_name", "未知事件")
        evt_type = event.get("event_type", "milestone")
        summary = event.get("summary", "")
        evidence = event.get("evidence", "")
        role = event.get("role", "witness")
        outcome = event.get("outcome", "")

        # Group by chapter
        if chapter != current_chapter:
            if current_chapter is not None:
                lines.append("")
            lines.append(f"### 第 {chapter} 章")
            current_chapter = chapter

        # Event entry
        type_label = EVENT_TYPE_DESCRIPTIONS.get(evt_type, evt_type).split(" - ")[0]
        role_label = {"subject": "主动", "object": "被动", "witness": "见证"}.get(
            role, role
        )

        lines.append(f"\n**{event_name}** [{type_label}] ({role_label})")

        if summary:
            lines.append(f"  - 摘要: {summary}")

        if outcome:
            lines.append(f"  - 结果: {outcome}")

        if evidence:
            # Truncate long evidence
            evidence_short = (
                evidence[:100] + "..." if len(evidence) > 100 else evidence
            )
            lines.append(f"  - 证据: \"{evidence_short}\"")

    lines.append("")
    lines.append(f"共找到 {len(events)} 个重大事件。")
    lines.append("")
    lines.append(
        "**提示**: 如需详细剧情内容，请使用 search_memory 搜索特定事件。"
    )

    return "\n".join(lines)
