# Agent Tool Interface

This document defines the tools available to the ReAct Agent for querying the Genshin QA system.
It serves as the contract between the Agent Logic and the underlying Python implementation (`src.tools.wrappers`).

## Tool Definitions

| Tool Name | Arguments | Description |
| :--- | :--- | :--- |
| **`lookup_knowledge`** | `entity` (str)<br>`relation` (opt, str) | **Retrieve Static Facts (Official Setting)**.<br>Use for: "Who is X?", "What is X's element?", "Which region is X from?".<br>*Source*: Neo4j Graph (Dynamic Index). |
| **`find_connection`** | `entity1` (str)<br>`entity2` (str) | **Find Logical Connection**.<br>Use for: "How is X related to Y?". Finds the shortest logical path between two entities.<br>*Source*: Neo4j Graph (ShortestPath). |
| **`track_journey`** | `entity` (str)<br>`target` (opt, str) | **Track State Evolution**.<br>Use for: "How did X change?", "How did X become friends with Y?". Returns events sorted by Chapter.<br>*Source*: Neo4j Graph (Temporal Filter). |
| **`search_memory`** | `query` (str)<br>`sort_by` (opt: "relevance"\|"time")<br>`limit` (opt, int) | **Retrieve Content/Dialogue**.<br>Use for: "What did X say?", "Describe the fight scene". Returns actual quotes and text chunks.<br>- `sort_by="relevance"` (Default): Best semantic match.<br>- `sort_by="time"`: Chronological order (Story Flow).<br>*Source*: Qdrant Vector DB. |

## Usage Examples

### 1. Factual Question
**User**: "Who is Mavuika?"
**Agent**: `lookup_knowledge(entity="Mavuika")`

### 2. Relationship Output
**User**: "How does Kinich know Kachina?"
**Agent**: `find_connection(entity1="Kinich", entity2="Kachina")`

### 3. Story Evolution
**User**: "What happened to the Traveler in Natlan?"
**Agent**:
1. `track_journey(entity="Traveler")` -> Get key milestones.
2. `search_memory(query="Traveler arrival in Natlan", sort_by="time")` -> Get details. 
