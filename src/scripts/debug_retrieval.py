
import logging
import sys
from src.tools.wrappers import search_memory

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

def test_queries():
    queries = [
        # Queries from the trace
        {"query": "少女 重回世界 复活 苏醒", "sort_by": "relevance"},
        {"query": "少女 离开 月亮倒影 回到现实", "sort_by": "time"},
        {"query": "少女 离开 月亮倒影 成功 方法", "sort_by": "time"},
        {"query": "少女 离开 月亮倒影 结局", "sort_by": "time"},
    ]

    limits = [5, 10, 20]

    for q in queries:
        print(f"\n{'='*50}")
        print(f"Testing Query: {q['query']} (sort_by={q['sort_by']})")
        print(f"{'='*50}")
        
        for limit in limits:
            print(f"\n--- Limit: {limit} ---")
            results = search_memory(
                query=q["query"],
                sort_by=q["sort_by"],
                limit=limit
            )
            
            # Print simplified results (just Task/Event IDs and first line of text)
            # The tool wrapper returns formatted string, we need to parse or just print length/preview.
            # Wait, the wrapper returns a LIST of dicts? 
            # In `src/tools/wrappers.py`, search_memory returns List[Dict] or rerun results.
            # But `src/agent/agent.py` wraps it to return string. 
            # `src/tools/wrappers.py` returns List[Dict].
            
            if isinstance(results, list):
                print(f"Found {len(results)} chunks.")
                for i, res in enumerate(results):
                    payload = res.get('payload', {})
                    chapter = payload.get('chapter_number')
                    task = payload.get('task_id')
                    event = payload.get('event_order')
                    text = payload.get('text', '')[:50].replace('\n', ' ')
                    print(f"  [{i+1}] Ch{chapter} Task{task} Ev{event}: {text}...")
            else:
                print("Result format unexpected (not list).")

if __name__ == "__main__":
    test_queries()
