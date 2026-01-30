# Query Tools

This directory contains the formal interface definitions for the ReAct Agent's tools.

## Key Files

*   **[tool_interface.md](./tool_interface.md)**: The **Source of Truth** for the ReAct Agent. It lists all available tools, their parameters, and descriptions.

## Tools Overview

| Tool | Purpose |
| :--- | :--- |
| `lookup_knowledge` | Retrieve static facts/attributes from Neo4j. |
| `find_connection` | Find logical paths between entities in Neo4j. |
| `track_journey` | Track entity state evolution over time in Neo4j. |
| `search_memory` | Retrieve dialogue chunks/content from Qdrant. |

> **Note**: Implementation details (Python wrappers) are located in `src/tools/wrappers.py`.
