"""
知识图谱工具：find_connection - 查找两个实体之间的关系路径。

此工具在 Neo4j 知识图谱中查找最短连接路径。
返回逻辑链（非长文本）。
"""

from ..graph.searcher import GraphSearcher


def find_connection(entity1: str, entity2: str) -> str:
    """
    查找知识图谱中两个实体之间的连接路径。

    使用场景：
    - "努昂诺塔和少女是什么关系？" (entity1="努昂诺塔", entity2="少女")
    - "恰斯卡怎么认识旅行者？" (entity1="恰斯卡", entity2="旅行者")
    - 理解角色之间的社交/组织关系

    参数：
        entity1: 第一个实体名称。
        entity2: 第二个实体名称。

    返回：
        显示连接路径的逻辑链。
        示例："基尼奇 -[MEMBER_OF]-> 林冠之影 <-[ALLIED_WITH]- 旅行者"
        如果没有找到路径，返回建议使用其他工具的提示。
    """
    with GraphSearcher() as searcher:
        path = searcher.get_path_between(entity1, entity2)

    if not path:
        return (
            f"在知识图谱中未找到 '{entity1}' 和 '{entity2}' 之间的直接连接（4步以内）。\n\n"
            f"建议：\n"
            f"- 使用 lookup_knowledge 分别查看每个实体的关系。\n"
            f"- 使用 search_memory 搜索两者同时出现的故事内容。"
        )

    # 格式化路径为可读的链
    nodes = path["path_nodes"]
    relations = path["path_relations"]

    # 构建链：A -[关系1]-> B -[关系2]-> C
    chain_parts = [nodes[0]]
    for i, rel in enumerate(relations):
        chain_parts.append(f" -[{rel}]-> ")
        chain_parts.append(nodes[i + 1])

    chain = "".join(chain_parts)

    lines = [
        f"## 关系路径：{entity1} ↔ {entity2}",
        "",
        f"**路径**（{path['path_length']} 步）：",
        chain,
        "",
        "**路径中的节点：**",
    ]

    for node in nodes:
        lines.append(f"- {node}")

    return "\n".join(lines)
