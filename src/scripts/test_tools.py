"""
Verification script for Tool Wrappers.
Tests lookup_knowledge, find_connection, track_journey, and search_memory.
"""
import sys
import logging
from src.tools.wrappers import lookup_knowledge, find_connection, track_journey, search_memory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_tools():
    print("=== Testing Tool Wrappers ===")
    
    # 1. lookup_knowledge
    print("\n[1] Testing lookup_knowledge('恰斯卡')...")
    try:
        res = lookup_knowledge("恰斯卡")
        print(f"Result count: {res.get('count', 0)}")
        if res.get('entities'):
            print(f"Top entity: {res['entities'][0]}")
    except Exception as e:
        print(f"Failed: {e}")

    # 2. find_connection
    print("\n[2] Testing find_connection('基尼奇', '恰斯卡')...")
    try:
        res = find_connection("基尼奇", "恰斯卡")
        print(f"Status: {res['status']}")
        print(f"Path: {res.get('entities', [])}")
    except Exception as e:
        print(f"Failed: {e}")

    # 3. track_journey
    print("\n[3] Testing track_journey('旅行者')...")
    try:
        res = track_journey("旅行者")
        print(f"Events found: {len(res)}")
        for event in res[:3]:
            print(f"  - {event.get('chapter', '?')} : {event.get('relation')} -> {event.get('target')}")
    except Exception as e:
        print(f"Failed: {e}")

    # 4. search_memory (Time Sort)
    print("\n[4] Testing search_memory('纳塔', sort_by='time')...")
    try:
        # Note: This requires Qdrant to be running and populated
        res = search_memory("纳塔", sort_by="time", limit=3)
        print(f"Chunks found: {len(res)}")
        for chunk in res:
            payload = chunk.get('payload', {})
            print(f"  - Chapter {payload.get('chapter_number')}: {payload.get('text', '')[:50]}...")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_tools()
