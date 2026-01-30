"""
知识图谱工具：lookup_knowledge - 查询实体的静态信息和直接关系。

此工具查询 Neo4j 知识图谱获取实体的基本信息。
返回结构化数据（非长文本）。
"""

from typing import Optional

from ..graph.searcher import GraphSearcher


def lookup_knowledge(entity: str, relation: Optional[str] = None) -> str:
    """
    查询知识图谱获取实体（角色、组织、地点）的基本信息。

    使用场景：
    - "少女是谁？" (entity="少女")
    - "玛薇卡的称号是什么？" (entity="玛薇卡")
    - "基尼奇的朋友有谁？" (entity="基尼奇", relation="FRIEND_OF")

    参数：
        entity: 实体名称（角色、组织或地点）。
                支持别名自动解析（如"火神"会解析为"玛薇卡"）。
        relation: 可选的关系类型过滤。
                  示例："FRIEND_OF"、"MEMBER_OF"、"PARTNER_OF"、"ENEMY_OF"

    返回：
        包含实体属性和直接关系的结构化文本。
        如果未找到信息，返回建议使用 search_memory 的提示。
    """
    with GraphSearcher() as searcher:
        result = searcher.search(entity, relation=relation, limit=10)

    if not result["entities"]:
        return f"在知识图谱中未找到 '{entity}' 的信息。建议使用 search_memory 搜索包含此实体的故事内容。"

    # 格式化输出为结构化文本
    lines = [f"## 实体信息：{result['entity']}"]

    if result["relation_filter"]:
        lines.append(f"(已过滤关系类型：{result['relation_filter']})")

    lines.append("")

    for item in result["entities"]:
        target = item.get("target", "未知")
        relation_type = item.get("relation", "RELATED_TO")
        target_type = item.get("target_type", "实体")
        description = item.get("description", "")
        rel_props = item.get("rel_properties", {})
        chapter = rel_props.get("chapter", "")
        task_id = rel_props.get("task_id", "")

        line = f"- [{relation_type}] → {target} ({target_type})"
        if chapter:
            line += f" [第{str(chapter)[:3]}章"
            if task_id:
                line += f", 任务{task_id}"
            line += "]"
        if description:
            line += f": {description[:100]}..."
        lines.append(line)

    lines.append("")
    lines.append(f"共找到 {result['count']} 条关系。")

    return "\n".join(lines)
