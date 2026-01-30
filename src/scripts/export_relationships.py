"""
Export Neo4j relationships to CSV and markdown report.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def export_relationships():
    """Export all relationships from Neo4j."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    results = {}

    with driver.session() as session:
        # 1. Relationship type counts
        query_counts = """
        MATCH ()-[r]->()
        RETURN type(r) AS relationship_type, count(r) AS count
        ORDER BY count DESC
        """
        result = session.run(query_counts)
        results["counts"] = [dict(r) for r in result]

        # 2. All relationships with details
        query_all = """
        MATCH (a)-[r]->(b)
        RETURN
            coalesce(a.name, a.title, toString(id(a))) AS source,
            labels(a)[0] AS source_type,
            type(r) AS relationship,
            coalesce(b.name, b.title, toString(id(b))) AS target,
            labels(b)[0] AS target_type,
            properties(r) AS properties
        ORDER BY type(r), source
        """
        result = session.run(query_all)
        results["relationships"] = [dict(r) for r in result]

        # 3. Character relationships
        query_chars = """
        MATCH (c1:Character)-[r]->(c2:Character)
        RETURN
            c1.name AS from_character,
            type(r) AS relationship,
            c2.name AS to_character,
            properties(r) AS properties
        ORDER BY type(r), c1.name
        """
        result = session.run(query_chars)
        results["character_relationships"] = [dict(r) for r in result]

        # 4. Organization memberships
        query_orgs = """
        MATCH (c:Character)-[r:MEMBER_OF]->(o:Organization)
        RETURN
            c.name AS character,
            o.name AS organization,
            r.role AS role
        ORDER BY o.name, c.name
        """
        result = session.run(query_orgs)
        results["memberships"] = [dict(r) for r in result]

    driver.close()
    return results


def generate_report(results: dict) -> str:
    """Generate markdown report from results."""
    lines = [
        "# Neo4j Relationships Export",
        "",
        f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## Relationship Type Summary",
        "",
        "| Type | Count |",
        "|------|-------|",
    ]

    total = 0
    for item in results["counts"]:
        lines.append(f"| {item['relationship_type']} | {item['count']} |")
        total += item["count"]

    lines.extend(["", f"**Total Relationships**: {total}", ""])

    # Character relationships
    lines.extend([
        "---",
        "",
        "## Character-to-Character Relationships",
        "",
        "| From | Relationship | To | Properties |",
        "|------|--------------|-----|------------|",
    ])

    for rel in results["character_relationships"]:
        props = rel.get("properties", {})
        props_str = ", ".join(f"{k}={v}" for k, v in props.items()) if props else "-"
        lines.append(
            f"| {rel['from_character']} | {rel['relationship']} | {rel['to_character']} | {props_str} |"
        )

    # Organization memberships
    lines.extend([
        "",
        "---",
        "",
        "## Organization Memberships",
        "",
        "| Character | Organization | Role |",
        "|-----------|--------------|------|",
    ])

    for mem in results["memberships"]:
        role = mem.get("role") or "-"
        lines.append(f"| {mem['character']} | {mem['organization']} | {role} |")

    # All relationships
    lines.extend([
        "",
        "---",
        "",
        "## All Relationships",
        "",
        "| Source | Source Type | Relationship | Target | Target Type |",
        "|--------|-------------|--------------|--------|-------------|",
    ])

    for rel in results["relationships"]:
        lines.append(
            f"| {rel['source']} | {rel['source_type']} | {rel['relationship']} | {rel['target']} | {rel['target_type']} |"
        )

    return "\n".join(lines)


def main():
    print("Connecting to Neo4j...")
    print(f"  URI: {NEO4J_URI}")
    print(f"  User: {NEO4J_USER}")
    print()

    try:
        results = export_relationships()
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        sys.exit(1)

    # Print summary
    print("=" * 50)
    print("RELATIONSHIP TYPE SUMMARY")
    print("=" * 50)
    total = 0
    for item in results["counts"]:
        print(f"  {item['relationship_type']:20} : {item['count']}")
        total += item["count"]
    print("-" * 50)
    print(f"  {'TOTAL':20} : {total}")
    print()

    # Generate report
    report = generate_report(results)

    # Save report
    output_path = Path(__file__).parent.parent.parent / ".project" / "reports" / "neo4j_relationships_current.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()
