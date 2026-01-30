from src.graph.searcher import GraphSearcher

def test_api():
    print("Testing GraphSearcher API Upgrade...")
    searcher = GraphSearcher()
    
    # 1. Test Alias Resolution
    alias = "阿乔"
    print(f"\n1. Testing Alias Resolution for '{alias}'...")
    res = searcher.search(alias)
    print(f"Results for '{alias}': Found {res['count']} relations.")
    if res['count'] > 0:
        print(f"First result source: {res['entities'][0]['source']}") # Should be "阿尤"
        
    # 2. Test History
    print(f"\n2. Testing History for '玩家' (Player)...")
    history = searcher.search_history("玩家", "派蒙")
    print(f"Found {len(history)} history events for Player -> Paimon:")
    for event in history:
        print(f"  [{event['chapter']}] {event['relation']}: {event['evidence'][:30]}...")

    searcher.close()

if __name__ == "__main__":
    test_api()
