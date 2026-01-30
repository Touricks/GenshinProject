from src.graph.searcher import GraphSearcher
from src.graph.connection import Neo4jConnection

def debug_alias():
    print("DEBUG: Resolving '阿乔'...")
    searcher = GraphSearcher()
    
    # 1. Direct Index Call (Top 5)
    query = """
            CALL db.index.fulltext.queryNodes("entity_alias_index", $name) 
            YIELD node, score 
            RETURN node.name as name, node.aliases as aliases, score 
            LIMIT 5
        """
    res = searcher.conn.execute(query, {"name": "阿乔"})
    print(f"Direct Query Result: {res}")
    
    # 2. Test Resolved Name Logic
    resolved = searcher._resolve_canonical_name("阿乔")
    print(f"Resolved Name: '{resolved}'")
    
    # Check relations for 阿尤
    print("\nChecking relations for '阿尤'...")
    res_ayu = searcher.search("阿尤")
    print(f"Relations for '阿尤': {res_ayu['count']}")
    
    searcher.close()

if __name__ == "__main__":
    debug_alias()
