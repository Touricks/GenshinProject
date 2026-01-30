from src.graph.connection import Neo4jConnection

def analyze_graph():
    conn = Neo4jConnection()
    
    print("--- 1. Relationships by Chapter ---")
    res = conn.execute("MATCH ()-[r]->() RETURN r.chapter as ch, count(r) as count ORDER BY ch")
    for r in res:
        print(f"Chapter {r['ch']}: {r['count']} relationships")

    print("\n--- 2. Temporal Evolution (Pairs with multiples) ---")
    query = """
    MATCH (a)-[r]->(b)
    WITH a, b, type(r) as Type, count(r) as Count, collect(r.chapter) as Chapters
    WHERE Count > 1
    RETURN a.name, b.name, Type, Count, Chapters
    LIMIT 10
    """
    res = conn.execute(query)
    if not res:
        print("No pairs found with multiple temporal edges.")
    else:
        for r in res:
            print(f"{r['a.name']} --[{r['Type']}]--> {r['b.name']} : {r['Count']} times (Chapters: {r['Chapters']})")

    print("\n--- 3. Verify Alias Index ---")
    res = conn.execute("SHOW INDEXES YIELD name, labelsOrTypes, properties WHERE name = 'entity_alias_index'")
    if res:
        print(f"Index found: {res[0]['name']} on {res[0]['labelsOrTypes']} {res[0]['properties']}")
    else:
        print("Alias Index NOT found!")

    # Test Alias Query
    print("\n--- 4. Alias Resolution Test (Scaramouche) ---")
    # Verify we can find '流浪者' via alias if it exists, or just test any character with alias.
    # Let's try to query '派蒙' (Paimon) or 'Traveler'.
    # Or query a known alias if we have one.
    
if __name__ == "__main__":
    analyze_graph()
