"""
Data ingestion pipeline for processing dialogue files.

This module provides:
- DocumentLoader: Parse dialogue files from Data/ directory
- SceneChunker: Scene-based semantic chunking
- MetadataEnricher: Extract characters and compute metadata
- EmbeddingGenerator: Generate embeddings using BGE model
- VectorIndexer: Index to Qdrant vector database
- JinaReranker: Rerank search results using Jina Reranker v2
- IngestionPipeline: Orchestrate the full pipeline
- EntityExtractor: Extract entities for graph building (regex-based)
- RelationExtractor: Extract relationships for graph building

LLM-based Knowledge Graph Extraction:
- LLMKnowledgeGraphExtractor: LLM-based entity/relationship extraction
- KnowledgeGraphOutput: Pydantic model for KG extraction results
- ExtractedEntity, ExtractedRelationship: Pydantic models for extracted data
- KGCache, CachedKGExtractor: Caching layer for LLM extraction
- IncrementalKGExtractor, KGMerger: Incremental extraction with deduplication
- KGSnapshotManager: Versioned KG snapshots
- CharacterValidator: Data quality validation for character names
"""

from .loader import DocumentLoader
from .chunker import SceneChunker
from .enricher import MetadataEnricher
from .embedder import EmbeddingGenerator
from .indexer import VectorIndexer
from .reranker import JinaReranker
from .pipeline import IngestionPipeline, run_pipeline
from .entity_extractor import EntityExtractor, extract_all_entities
from .relation_extractor import RelationExtractor, get_seed_relationships

# LLM-based KG extraction
from .llm_kg_extractor import (
    LLMKnowledgeGraphExtractor,
    KnowledgeGraphOutput,
    ExtractedEntity,
    ExtractedRelationship,
    extract_kg_from_text,
    extract_kg_from_file,
)
from .kg_cache import KGCache, CachedKGExtractor
from .incremental_extractor import (
    IncrementalKGExtractor,
    KGMerger,
    FileTrackingInfo,
)
from .kg_snapshot import KGSnapshotManager
from .character_validator import (
    CharacterValidator,
    InvalidReason,
    ValidationResult,
    validate_character_name,
    filter_character_names,
)

__all__ = [
    # Vector DB pipeline
    "DocumentLoader",
    "SceneChunker",
    "MetadataEnricher",
    "EmbeddingGenerator",
    "VectorIndexer",
    "JinaReranker",
    "IngestionPipeline",
    "run_pipeline",
    # Regex-based extraction
    "EntityExtractor",
    "RelationExtractor",
    "extract_all_entities",
    "get_seed_relationships",
    # LLM-based KG extraction
    "LLMKnowledgeGraphExtractor",
    "KnowledgeGraphOutput",
    "ExtractedEntity",
    "ExtractedRelationship",
    "extract_kg_from_text",
    "extract_kg_from_file",
    "KGCache",
    "CachedKGExtractor",
    "IncrementalKGExtractor",
    "KGMerger",
    "FileTrackingInfo",
    "KGSnapshotManager",
    # Data quality validation
    "CharacterValidator",
    "InvalidReason",
    "ValidationResult",
    "validate_character_name",
    "filter_character_names",
]
