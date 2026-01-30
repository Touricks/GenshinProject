from src.graph.connection import Neo4jConnection
from tabulate import tabulate
import os

def generate_report():
    conn = Neo4jConnection()
    if not conn.verify_connectivity():
        print("Failed to connect to Neo4j")
        return

    report_lines = ["# Neo4j Knowledge Graph Statistics Report", ""]

    # 1. Node Counts
    report_lines.append("## Node Counts")
    query_nodes = "MATCH (n) RETURN labels(n)[0] as Label, count(n) as Count ORDER BY Count DESC"
    nodes_data = conn.execute(query_nodes)
    if nodes_data:
        headers = nodes_data[0].keys()
        rows = [[item[h] for h in headers] for item in nodes_data]
        report_lines.append(tabulate(rows, headers=headers, tablefmt="github"))
    report_lines.append("")

    # 2. Relationship Counts
    report_lines.append("## Relationship Counts")
    query_rels = "MATCH ()-[r]->() RETURN type(r) as Type, count(r) as Count ORDER BY Count DESC"
    rels_data = conn.execute(query_rels)
    if rels_data:
        headers = rels_data[0].keys()
        rows = [[item[h] for h in headers] for item in rels_data]
        report_lines.append(tabulate(rows, headers=headers, tablefmt="github"))
    report_lines.append("")

    # 3. Top 10 Most Connected Characters
    report_lines.append("## Top 10 Most Connected Characters")
    query_top_chars = """
    MATCH (c:Character)-[r]-()
    RETURN c.name as Name, count(r) as Connections
    ORDER BY Connections DESC
    LIMIT 10
    """
    top_chars_data = conn.execute(query_top_chars)
    if top_chars_data:
        headers = top_chars_data[0].keys()
        rows = [[item[h] for h in headers] for item in top_chars_data]
        report_lines.append(tabulate(rows, headers=headers, tablefmt="github"))
    report_lines.append("")

    # 4. Characters by Tribe (Natlan)
    report_lines.append("## Characters by Tribe (Natlan)")
    query_tribes = """
    MATCH (c:Character)
    WHERE c.tribe IS NOT NULL
    RETURN c.tribe as Tribe, count(c) as Count, collect(c.name) as Members
    ORDER BY Count DESC
    """
    tribes_data = conn.execute(query_tribes)
    if tribes_data:
        # Format members list for better display
        for item in tribes_data:
            if len(item['Members']) > 5:
                item['Members'] = ", ".join(item['Members'][:5]) + f" and {len(item['Members'])-5} more"
            else:
                item['Members'] = ", ".join(item['Members'])
        
        headers = ["Tribe", "Count", "Members"]
        rows = [[item[h] for h in ["Tribe", "Count", "Members"]] for item in tribes_data]
        report_lines.append(tabulate(rows, headers=headers, tablefmt="github"))
    report_lines.append("")
    
    # 5. Organizations by Type
    report_lines.append("## Organizations by Type")
    query_orgs = """
    MATCH (o:Organization)
    RETURN o.type as Type, count(o) as Count, collect(o.name) as Organizations
    ORDER BY Count DESC
    """
    orgs_data = conn.execute(query_orgs)
    if orgs_data:
         # Format members list for better display
        for item in orgs_data:
            item['Organizations'] = ", ".join(item['Organizations'])

        headers = ["Type", "Count", "Organizations"]
        rows = [[item[h] for h in ["Type", "Count", "Organizations"]] for item in orgs_data]
        report_lines.append(tabulate(rows, headers=headers, tablefmt="github"))
    report_lines.append("")

    # Output
    report_content = "\n".join(report_lines)
    print(report_content)
    
    # Save to file
    output_path = ".project/neo4j_stats_report.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report_content)
    print(f"\nReport saved to {output_path}")

if __name__ == "__main__":
    generate_report()
