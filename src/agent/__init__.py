"""
Genshin Retrieval Agent module.

Provides the ReAct Agent for Genshin Story QA using LlamaIndex.

Usage:
    from src.agent import GenshinRetrievalAgent, create_agent

    # Option 1: Direct instantiation
    agent = GenshinRetrievalAgent(session_id="user123")

    # Option 2: Factory function
    agent = create_agent(session_id="user123", verbose=True)

    # Single query (stateless)
    response = await agent.run("Who is Mavuika?")

    # Multi-turn chat (preserves context)
    response = await agent.chat("Who is Mavuika?")
    response = await agent.chat("What are her abilities?")  # Remembers context
"""

from .agent import GenshinRetrievalAgent, create_agent
from .prompts import SYSTEM_PROMPT

__all__ = [
    "GenshinRetrievalAgent",
    "create_agent",
    "SYSTEM_PROMPT",
]
