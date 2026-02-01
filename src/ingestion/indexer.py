"""Vector indexer for Qdrant storage."""

import logging
from typing import List, Optional

from ..models import Chunk
from ..config import Settings

logger = logging.getLogger(__name__)


class VectorIndexer:
    """Index chunks into Qdrant vector store."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        collection_name: str = None,
        vector_size: int = None,
    ):
        """
        Initialize Qdrant indexer.

        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Name of the collection
            vector_size: Dimension of embedding vectors
        """
        settings = Settings()
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self.vector_size = vector_size or settings.EMBEDDING_DIM

        # Lazy load the client
        self._client = None

    @property
    def client(self):
        """Lazy load the Qdrant client."""
        if self._client is None:
            self._client = self._connect()
        return self._client

    def _connect(self):
        """Connect to Qdrant server."""
        try:
            from qdrant_client import QdrantClient
        except ImportError:
            raise ImportError(
                "qdrant-client is required. Install with: pip install qdrant-client"
            )

        logger.info(f"Connecting to Qdrant at {self.host}:{self.port}")
        client = QdrantClient(host=self.host, port=self.port)

        # Verify connection
        try:
            client.get_collections()
            logger.info("Connected to Qdrant successfully")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Qdrant: {e}")

        return client

    def ensure_collection(self) -> bool:
        """
        Create collection if it doesn't exist.

        Returns:
            True if collection was created, False if it already existed
        """
        from qdrant_client.models import Distance, VectorParams

        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if exists:
            logger.info(f"Collection '{self.collection_name}' already exists")
            return False

        logger.info(f"Creating collection '{self.collection_name}'")
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

        # Create payload indexes for filtering
        self._create_payload_indexes()

        logger.info(f"Collection '{self.collection_name}' created successfully")
        return True

    def _create_payload_indexes(self):
        """Create payload field indexes for efficient filtering."""
        from qdrant_client.models import PayloadSchemaType

        index_configs = [
            ("task_id", PayloadSchemaType.KEYWORD),
            ("chapter_number", PayloadSchemaType.INTEGER),
            ("characters", PayloadSchemaType.KEYWORD),
            ("event_order", PayloadSchemaType.INTEGER),
            ("series_name", PayloadSchemaType.KEYWORD),
        ]

        for field_name, field_type in index_configs:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_type,
                )
                logger.debug(f"Created index for field: {field_name}")
            except Exception as e:
                logger.warning(f"Failed to create index for {field_name}: {e}")

    def upsert_chunks(self, chunks: List[Chunk], batch_size: int = 100) -> int:
        """
        Upsert chunks with embeddings to Qdrant.

        Args:
            chunks: List of Chunk objects with embeddings
            batch_size: Number of points per upsert batch

        Returns:
            Number of points upserted
        """
        from qdrant_client.models import PointStruct

        # Filter chunks that have embeddings
        valid_chunks = [c for c in chunks if c.embedding is not None]

        if len(valid_chunks) < len(chunks):
            logger.warning(
                f"Skipping {len(chunks) - len(valid_chunks)} chunks without embeddings"
            )

        if not valid_chunks:
            logger.warning("No valid chunks to upsert")
            return 0

        # Convert to Qdrant points
        points = [
            PointStruct(
                id=hash(chunk.id) % (2**63),  # Convert string ID to int
                vector=chunk.embedding,
                payload={
                    "text": chunk.text,
                    **chunk.metadata.to_dict(),
                },
            )
            for chunk in valid_chunks
        ]

        # Batch upsert
        total_upserted = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
            )
            total_upserted += len(batch)
            logger.debug(f"Upserted batch {i // batch_size + 1}: {len(batch)} points")

        logger.info(f"Upserted {total_upserted} points to '{self.collection_name}'")
        return total_upserted

    def get_collection_info(self) -> dict:
        """Get information about the collection."""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "status": info.status.value,
        }

    def delete_collection(self) -> bool:
        """Delete the collection. Use with caution!"""
        logger.warning(f"Deleting collection '{self.collection_name}'")
        return self.client.delete_collection(self.collection_name)

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        filter_conditions: Optional[dict] = None,
        sort_by: str = "relevance",
    ) -> List[dict]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            limit: Number of results to return
            filter_conditions: Optional filter conditions.
                - 单值: {"field": "value"} → MatchValue
                - 多值: {"field": ["v1", "v2"]} → MatchAny (匹配任意一个)
            sort_by: Sort method ("relevance" or "time")

        Returns:
            List of search results with payload
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

        # Build filter if provided
        qdrant_filter = None
        if filter_conditions:
            conditions = []
            for field, value in filter_conditions.items():
                if isinstance(value, list):
                    # 多值匹配：使用 MatchAny
                    conditions.append(
                        FieldCondition(key=field, match=MatchAny(any=value))
                    )
                else:
                    # 单值匹配：使用 MatchValue
                    conditions.append(
                        FieldCondition(key=field, match=MatchValue(value=value))
                    )
            qdrant_filter = Filter(must=conditions)

        # For time sorting, we might want to fetch more candidates to ensure
        # we have a good timeline coverage, but for now we stick to limit.
        search_limit = limit if sort_by == "relevance" else limit * 2

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=search_limit,
            query_filter=qdrant_filter,
        )

        results = [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload,
            }
            for r in response.points
        ]

        if sort_by == "time":
            # Sort by chapter_number first, then event_order
            # Default to 0 if missing
            results.sort(
                key=lambda x: (
                    x["payload"].get("chapter_number", 0),
                    x["payload"].get("event_order", 0),
                )
            )
            # Trim strictly back to limit? Or keep the expanded context?
            # Usually strict limit is expected by the caller.
            results = results[:limit]

        return results
