"""
Tool wrappers for the ReAct Agent.
Implements the interface defined in docs/query/openapi.yaml.
"""

from typing import List, Optional, Dict, Any
from llama_index.core.tools import FunctionTool
from src.graph.searcher import GraphSearcher
from src.ingestion.indexer import VectorIndexer
from src.ingestion.embedder import EmbeddingGenerator
from src.ingestion.reranker import JinaReranker

# Global instances (Lazy loaded if possible, but for tools usually instantiated once)
# In a real app, use dependency injection or a service container.
_graph_searcher = None
_vector_indexer = None
_embedder = None
_reranker = None

def get_graph_searcher():
    global _graph_searcher
    if _graph_searcher is None:
        _graph_searcher = GraphSearcher()
    return _graph_searcher

def get_vector_indexer():
    global _vector_indexer
    if _vector_indexer is None:
        _vector_indexer = VectorIndexer()
    return _vector_indexer

def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingGenerator()
    return _embedder

def get_reranker():
    global _reranker
    if _reranker is None:
        # Top K after reranking can be 5 by default
        _reranker = JinaReranker(top_k=5)
    return _reranker


def lookup_knowledge(entity: str, relation: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve static facts and relationships about an entity (Character, Organization, etc.) from the Knowledge Graph.
    
    Use this to answer "Who is X?", "What is X's role?", "Who are X's friends?".
    DO NOT use this for plot details or specific events.

    Args:
        entity: Name of the entity (e.g., "Mavuika", "Fatui").
        relation: Optional filter for relationship type (e.g., "FRIEND_OF", "MEMBER_OF").
    """
    searcher = get_graph_searcher()
    return searcher.search(entity, relation=relation, limit=15)


def find_connection(entity1: str, entity2: str) -> Dict[str, Any]:
    """
    Find the shortest logical connection/path between two entities.
    
    Use this to answer "How is X related to Y?".
    
    Args:
        entity1: Start entity name.
        entity2: Target entity name.
    """
    searcher = get_graph_searcher()
    path = searcher.get_path_between(entity1, entity2)
    
    if not path:
        return {"status": "No connection found", "path": []}
        
    return {
        "status": "Connection found",
        "entities": path["path_nodes"],
        "relations": path["path_relations"]
    }


def track_journey(entity: str, target: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Track the evolution of an entity's state or relationship over time (chapters).
    
    Use this to answer "How did X change?", "How did X become friends with Y?".
    
    Args:
        entity: The main entity to track.
        target: Optional specific target entity to track relationship with.
    """
    searcher = get_graph_searcher()
    return searcher.search_history(entity, target=target)


def search_memory(
    query: str, 
    sort_by: str = "relevance", 
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieve specific dialogue chunks or plot details from vector memory.
    
    Use this to find quotes, descriptions of events, or specific conversations.
    
    Args:
        query: Natural language query string (e.g. "What did Paimon say about the fire?").
        sort_by: "relevance" (semantic similarity) or "time" (chronological order).
        limit: Max number of chunks to return.
    """
    indexer = get_vector_indexer()
    embedder = get_embedder()
    
    # 1. Embed Query
    query_vector = embedder.embed_single(query)
    
    # 2. Vector Search (pass sort_by to indexer)
    # If sort_by="time", indexer handles post-retrieval sorting
    results = indexer.search(
        query_vector=query_vector, 
        limit=limit, 
        sort_by=sort_by
    )
    
    # 3. Rerank (Only if sorting by relevance)
    # If sorting by time, we respect the time order and do not re-shuffle by score.
    if sort_by == "relevance" and results:
        reranker = get_reranker()
        # Extract text for reranker
        reranked_results = reranker.rerank_with_metadata(
            query=query,
            results=results,
            text_key="text", # Assuming payload has 'text'
            top_k=limit
        )
        return reranked_results
        
    return results

# List of Tools for Agent
def get_tools() -> List[FunctionTool]:
    return [
        FunctionTool.from_defaults(fn=lookup_knowledge),
        FunctionTool.from_defaults(fn=find_connection),
        FunctionTool.from_defaults(fn=track_journey),
        FunctionTool.from_defaults(fn=search_memory),
    ]
