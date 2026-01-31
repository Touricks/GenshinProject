"""
Verification script for Retrieval Tools.
Tests lookup_knowledge, find_connection, track_journey, search_memory, and get_character_events.
"""
import logging
from src.retrieval import (
    lookup_knowledge,
    find_connection,
    track_journey,
    search_memory,
    get_character_events,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_tools():
    print("=== Testing Retrieval Tools ===")

    # 1. lookup_knowledge
    print("\n[1] Testing lookup_knowledge('恰斯卡')...")
    try:
        res = lookup_knowledge("恰斯卡")
        print(f"Result:\n{res[:500]}..." if len(res) > 500 else f"Result:\n{res}")
    except Exception as e:
        print(f"Failed: {e}")

    # 2. find_connection
    print("\n[2] Testing find_connection('基尼奇', '恰斯卡')...")
    try:
        res = find_connection("基尼奇", "恰斯卡")
        print(f"Result:\n{res}")
    except Exception as e:
        print(f"Failed: {e}")

    # 3. track_journey
    print("\n[3] Testing track_journey('旅行者')...")
    try:
        res = track_journey("旅行者")
        print(f"Result:\n{res[:500]}..." if len(res) > 500 else f"Result:\n{res}")
    except Exception as e:
        print(f"Failed: {e}")

    # 4. search_memory
    print("\n[4] Testing search_memory('纳塔', sort_by='time')...")
    try:
        res = search_memory("纳塔", sort_by="time", limit=3)
        print(f"Result:\n{res[:500]}..." if len(res) > 500 else f"Result:\n{res}")
    except Exception as e:
        print(f"Failed: {e}")

    # 5. get_character_events (NEW)
    print("\n[5] Testing get_character_events('少女')...")
    try:
        res = get_character_events("少女")
        print(f"Result:\n{res[:500]}..." if len(res) > 500 else f"Result:\n{res}")
    except Exception as e:
        print(f"Failed: {e}")


if __name__ == "__main__":
    test_tools()
