"""
合并木偶/桑多涅重复节点脚本。

将 '木偶' 和 '「木偶」' 节点的所有关系迁移到 '桑多涅' 节点，
然后更新别名、重建索引、删除旧节点。

Usage:
    python scripts/merge_puppet_nodes.py [--dry-run]
"""

import argparse
import os
import sys
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

load_dotenv()


class Neo4jConnection:
    """Simplified Neo4j connection for this script."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "genshin_story_qa")
        self._driver: Optional[Driver] = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def verify_connectivity(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"Neo4j connection failed: {e}")
            return False

    @contextmanager
    def session(self, database: str = "neo4j"):
        session = self.driver.session(database=database)
        try:
            yield session
        finally:
            session.close()

    def execute(
        self, query: str, params: Optional[Dict[str, Any]] = None, database: str = "neo4j"
    ) -> List[Dict[str, Any]]:
        with self.session(database=database) as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]

    def execute_write(
        self, query: str, params: Optional[Dict[str, Any]] = None, database: str = "neo4j"
    ) -> List[Dict[str, Any]]:
        with self.session(database=database) as session:
            result = session.execute_write(
                lambda tx: list(tx.run(query, params or {}))
            )
            return [dict(record) for record in result]


def check_current_state(conn: Neo4jConnection) -> dict:
    """检查当前节点状态。"""
    print("\n=== 检查当前节点状态 ===")

    query = """
        MATCH (c:Character)
        WHERE c.name IN ['木偶', '「木偶」', '桑多涅']
        OPTIONAL MATCH (c)-[r]-()
        RETURN c.name as name, c.aliases as aliases, count(r) as rel_count
    """
    results = conn.execute(query)

    state = {}
    for row in results:
        name = row["name"]
        state[name] = {
            "aliases": row["aliases"],
            "rel_count": row["rel_count"],
        }
        print(f"  节点 '{name}': 别名={row['aliases']}, 关系数={row['rel_count']}")

    return state


def get_relationship_details(conn: Neo4jConnection, node_name: str) -> list:
    """获取节点的所有关系详情。"""
    query = """
        MATCH (c:Character {name: $name})-[r]-(other)
        RETURN type(r) as rel_type,
               startNode(r).name as start_name,
               endNode(r).name as end_name,
               properties(r) as props,
               labels(other)[0] as other_label
    """
    return conn.execute(query, {"name": node_name})


def migrate_relationships(
    conn: Neo4jConnection, old_name: str, new_name: str, dry_run: bool = False
) -> int:
    """
    将旧节点的所有关系迁移到新节点。

    由于不依赖 APOC，采用手动迁移方式：
    1. 查询所有关系
    2. 为每个关系在新节点上创建对应关系
    3. 删除旧关系
    """
    print(f"\n--- 迁移 '{old_name}' -> '{new_name}' ---")

    # 获取所有关系
    rels = get_relationship_details(conn, old_name)
    print(f"  发现 {len(rels)} 条关系需要迁移")

    if dry_run:
        for rel in rels:
            direction = "->" if rel["start_name"] == old_name else "<-"
            other = rel["end_name"] if rel["start_name"] == old_name else rel["start_name"]
            print(f"    [DRY-RUN] {rel['rel_type']} {direction} {other}")
        return len(rels)

    migrated_count = 0

    for rel in rels:
        rel_type = rel["rel_type"]
        props = rel["props"] or {}
        is_outgoing = rel["start_name"] == old_name
        other_name = rel["end_name"] if is_outgoing else rel["start_name"]
        other_label = rel["other_label"]

        # 构建属性字符串
        props_str = ", ".join(f"{k}: ${k}" for k in props.keys()) if props else ""
        props_clause = f" {{{props_str}}}" if props_str else ""

        if is_outgoing:
            # 出边: (old)-[r]->(other) => (new)-[r]->(other)
            create_query = f"""
                MATCH (new:Character {{name: $new_name}})
                MATCH (other:{other_label} {{name: $other_name}})
                MERGE (new)-[r:{rel_type}{props_clause}]->(other)
                RETURN count(*) as created
            """
        else:
            # 入边: (other)-[r]->(old) => (other)-[r]->(new)
            create_query = f"""
                MATCH (new:Character {{name: $new_name}})
                MATCH (other:{other_label} {{name: $other_name}})
                MERGE (other)-[r:{rel_type}{props_clause}]->(new)
                RETURN count(*) as created
            """

        params = {"new_name": new_name, "other_name": other_name, **props}

        try:
            conn.execute_write(create_query, params)
            migrated_count += 1
            direction = "->" if is_outgoing else "<-"
            print(f"    迁移: {rel_type} {direction} {other_name}")
        except Exception as e:
            print(f"    [ERROR] 迁移失败 {rel_type} -> {other_name}: {e}")

    return migrated_count


def update_aliases(conn: Neo4jConnection, dry_run: bool = False) -> None:
    """更新桑多涅的别名列表。"""
    print("\n=== 更新别名 ===")

    query = """
        MATCH (c:Character {name: '桑多涅'})
        SET c.aliases = ['木偶', '「木偶」']
        RETURN c.name, c.aliases
    """

    if dry_run:
        print("  [DRY-RUN] 将设置 aliases = ['木偶', '「木偶」']")
        return

    result = conn.execute_write(query)
    if result:
        print(f"  更新完成: {result[0]}")
    else:
        print("  [WARN] 未找到桑多涅节点")


def rebuild_fulltext_index(conn: Neo4jConnection, dry_run: bool = False) -> None:
    """重建 fulltext 索引以包含新别名。"""
    print("\n=== 重建 Fulltext 索引 ===")

    if dry_run:
        print("  [DRY-RUN] 将删除并重建 entity_alias_index")
        return

    # 先检查索引是否存在
    check_query = """
        SHOW INDEXES
        WHERE name = 'entity_alias_index'
    """
    existing = conn.execute(check_query)

    if existing:
        # 删除现有索引
        try:
            conn.execute_write("DROP INDEX entity_alias_index IF EXISTS")
            print("  已删除旧索引")
        except Exception as e:
            print(f"  [WARN] 删除索引时出错 (可能不存在): {e}")

    # 创建新索引
    create_query = """
        CREATE FULLTEXT INDEX entity_alias_index IF NOT EXISTS
        FOR (n:Character|Organization)
        ON EACH [n.name, n.aliases]
    """
    try:
        conn.execute_write(create_query)
        print("  已创建新索引 entity_alias_index")
    except Exception as e:
        print(f"  [ERROR] 创建索引失败: {e}")


def delete_old_nodes(conn: Neo4jConnection, dry_run: bool = False) -> None:
    """删除已迁移的旧节点。"""
    print("\n=== 删除旧节点 ===")

    old_names = ["木偶", "「木偶」"]

    for name in old_names:
        if dry_run:
            print(f"  [DRY-RUN] 将删除节点 '{name}'")
            continue

        query = """
            MATCH (c:Character {name: $name})
            DETACH DELETE c
            RETURN count(*) as deleted
        """
        try:
            conn.execute_write(query, {"name": name})
            print(f"  已删除节点 '{name}'")
        except Exception as e:
            print(f"  [ERROR] 删除 '{name}' 失败: {e}")


def deduplicate_relationships(conn: Neo4jConnection, dry_run: bool = False) -> None:
    """去重合并后可能产生的重复关系。"""
    print("\n=== 去重关系 ===")

    # 常见关系类型
    rel_types = [
        "MEMBER_OF",
        "FRIEND_OF",
        "PARTNER_OF",
        "ENEMY_OF",
        "FAMILY_OF",
        "INTERACTS_WITH",
        "LEADER_OF",
        "EXPERIENCES",
    ]

    for rel_type in rel_types:
        # 查找重复关系
        check_query = f"""
            MATCH (c:Character {{name: '桑多涅'}})-[r:{rel_type}]->(other)
            WITH c, other, collect(r) as rels
            WHERE size(rels) > 1
            RETURN other.name as other_name, size(rels) as dup_count
        """
        duplicates = conn.execute(check_query)

        if not duplicates:
            continue

        for dup in duplicates:
            if dry_run:
                print(
                    f"  [DRY-RUN] {rel_type} -> {dup['other_name']}: "
                    f"将删除 {dup['dup_count'] - 1} 条重复"
                )
                continue

            # 删除重复关系，保留第一条
            dedup_query = f"""
                MATCH (c:Character {{name: '桑多涅'}})-[r:{rel_type}]->(other {{name: $other_name}})
                WITH c, other, collect(r) as rels
                WHERE size(rels) > 1
                FOREACH (r in tail(rels) | DELETE r)
                RETURN size(rels) - 1 as deleted
            """
            result = conn.execute_write(dedup_query, {"other_name": dup["other_name"]})
            if result:
                print(
                    f"  {rel_type} -> {dup['other_name']}: 删除 {result[0].get('deleted', 0)} 条重复"
                )


def verify_result(conn: Neo4jConnection) -> bool:
    """验证合并结果。"""
    print("\n=== 验证结果 ===")

    # 检查节点状态
    query = """
        MATCH (c:Character)
        WHERE c.name IN ['木偶', '「木偶」', '桑多涅']
        RETURN c.name as name, c.aliases as aliases
    """
    results = conn.execute(query)

    found_names = [r["name"] for r in results]
    print(f"  找到的节点: {found_names}")

    if "木偶" in found_names or "「木偶」" in found_names:
        print("  [FAIL] 旧节点仍然存在!")
        return False

    if "桑多涅" not in found_names:
        print("  [FAIL] 桑多涅节点不存在!")
        return False

    # 检查别名
    sandone = next((r for r in results if r["name"] == "桑多涅"), None)
    if sandone:
        aliases = sandone.get("aliases") or []
        if "木偶" in aliases and "「木偶」" in aliases:
            print(f"  [OK] 别名正确: {aliases}")
        else:
            print(f"  [WARN] 别名不完整: {aliases}")

    # 检查关系数量
    rel_query = """
        MATCH (c:Character {name: '桑多涅'})-[r]-()
        RETURN count(r) as rel_count
    """
    rel_result = conn.execute(rel_query)
    if rel_result:
        print(f"  [OK] 桑多涅关系数量: {rel_result[0]['rel_count']}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="合并木偶/桑多涅重复节点",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示将要执行的操作，不实际修改数据库",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("合并木偶/桑多涅重复节点")
    print("=" * 60)

    if args.dry_run:
        print("\n*** DRY-RUN 模式 - 不会修改数据库 ***\n")

    conn = Neo4jConnection()

    if not conn.verify_connectivity():
        print("[ERROR] 无法连接到 Neo4j 数据库")
        sys.exit(1)

    try:
        # Step 0: 检查当前状态
        state = check_current_state(conn)

        if "桑多涅" not in state:
            print("\n[ERROR] 未找到桑多涅节点，请先确认节点名称")
            sys.exit(1)

        # Step 1: 迁移关系
        total_migrated = 0
        for old_name in ["木偶", "「木偶」"]:
            if old_name in state:
                migrated = migrate_relationships(conn, old_name, "桑多涅", args.dry_run)
                total_migrated += migrated

        print(f"\n共迁移 {total_migrated} 条关系")

        # Step 2: 更新别名
        update_aliases(conn, args.dry_run)

        # Step 3: 重建索引
        rebuild_fulltext_index(conn, args.dry_run)

        # Step 4: 删除旧节点
        delete_old_nodes(conn, args.dry_run)

        # Step 5: 去重关系
        deduplicate_relationships(conn, args.dry_run)

        # 验证
        if not args.dry_run:
            success = verify_result(conn)
            if success:
                print("\n[SUCCESS] 合并完成!")
            else:
                print("\n[WARN] 合并完成但验证未通过，请检查数据")
        else:
            print("\n[DRY-RUN] 预演完成，使用不带 --dry-run 参数运行以执行实际操作")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
