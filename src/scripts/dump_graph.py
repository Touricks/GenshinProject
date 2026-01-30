from src.graph.connection import Neo4jConnection
import sys

def generate_full_report():
    conn = Neo4jConnection()
    if not conn.verify_connectivity():
        print("Cannot connect to Neo4j")
        return

    report_lines = []
    report_lines.append("# Neo4j Graph Content Report (Data/1608)")
    report_lines.append("\n## 1. Node Statistics")
    
    # Count nodes
    res = conn.execute("MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC")
    report_lines.append("| Label | Count |")
    report_lines.append("|-------|-------|")
    for r in res:
        report_lines.append(f"| {r['label']} | {r['count']} |")

    # List all Characters
    report_lines.append("\n## 2. All Characters")
    res = conn.execute("MATCH (c:Character) RETURN c.name as name, c.description as desc ORDER BY c.name")
    for r in res:
        desc = r.get('desc', 'N/A')
        # truncated description for readability
        if desc and len(desc) > 50:
            desc = desc[:50] + "..."
        report_lines.append(f"- **{r['name']}**: {desc}")

    # List all Organizations
    report_lines.append("\n## 3. All Organizations")
    res = conn.execute("MATCH (o:Organization) RETURN o.name as name, o.type as type ORDER BY o.name")
    for r in res:
        report_lines.append(f"- **{r['name']}** ({r.get('type', 'unknown')})")

    # List all Relationships with Evidence
    report_lines.append("\n## 4. All Relationships & Evidence")
    report_lines.append("| Source | Relation | Target | Evidence |")
    report_lines.append("|--------|----------|--------|----------|")
    
    query = """
    MATCH (a)-[r]->(b) 
    RETURN a.name as source, type(r) as type, b.name as target, r.evidence as evidence
    ORDER BY type, source
    """
    res = conn.execute(query)
    
    for r in res:
        evidence = r.get('evidence', '')
        if evidence:
            # Escape pipes for markdown table
            evidence = evidence.replace('|', '\|').replace('\n', ' ')
            if len(evidence) > 100:
                evidence = evidence[:100] + "..."
            evidence = f"`{evidence}`"
        else:
            evidence = "*(Seed/No Text)*"
            
        report_lines.append(f"| {r['source']} | {r['type']} | {r['target']} | {evidence} |")

    # Write to file
    report_content = "\n".join(report_lines)
    output_path = ".project/graph_content_1608.md"
    with open(output_path, "w") as f:
        f.write(report_content)
    
    print(f"Report saved to {output_path}")

if __name__ == "__main__":
    generate_full_report()
