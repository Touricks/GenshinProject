"""Integration tests for VectorIndexer."""

import pytest


@pytest.mark.integration
class TestVectorIndexerConnection:
    """Test Qdrant connection and basic operations."""

    def test_connection(self, qdrant_client):
        """Test that Qdrant is accessible."""
        collections = qdrant_client.get_collections()
        assert collections is not None

    def test_indexer_connects(self, test_indexer):
        """Test VectorIndexer connects successfully."""
        # Accessing client property triggers connection
        client = test_indexer.client
        assert client is not None


@pytest.mark.integration
class TestCollectionManagement:
    """Test collection creation and deletion."""

    def test_create_collection(self, test_indexer):
        """Test collection creation with correct config."""
        created = test_indexer.ensure_collection()
        assert created is True

        # Verify collection exists
        info = test_indexer.get_collection_info()
        assert info["name"] == "test_genshin_story"
        assert info["vectors_count"] == 0

    def test_create_collection_idempotent(self, test_indexer):
        """Test that ensure_collection is idempotent."""
        # First call creates
        created1 = test_indexer.ensure_collection()
        assert created1 is True

        # Second call does nothing
        created2 = test_indexer.ensure_collection()
        assert created2 is False

    def test_delete_collection(self, test_indexer):
        """Test collection deletion."""
        test_indexer.ensure_collection()
        deleted = test_indexer.delete_collection()
        assert deleted is True

    def test_get_collection_info(self, test_indexer):
        """Test getting collection information."""
        test_indexer.ensure_collection()
        info = test_indexer.get_collection_info()

        assert "name" in info
        assert "vectors_count" in info
        assert "points_count" in info
        assert "status" in info


@pytest.mark.integration
class TestChunkUpsert:
    """Test chunk upsert operations."""

    def test_upsert_single_chunk(self, test_indexer, sample_chunks_with_embeddings):
        """Test upserting a single chunk."""
        test_indexer.ensure_collection()

        chunk = sample_chunks_with_embeddings[0]
        count = test_indexer.upsert_chunks([chunk])

        assert count == 1

        info = test_indexer.get_collection_info()
        assert info["points_count"] == 1

    def test_upsert_batch(self, test_indexer, sample_chunks_with_embeddings):
        """Test batch upserting multiple chunks."""
        test_indexer.ensure_collection()

        count = test_indexer.upsert_chunks(sample_chunks_with_embeddings)

        assert count == len(sample_chunks_with_embeddings)

        info = test_indexer.get_collection_info()
        assert info["points_count"] == len(sample_chunks_with_embeddings)

    def test_upsert_without_embedding_skipped(self, test_indexer, sample_chunks):
        """Test that chunks without embeddings are skipped."""
        test_indexer.ensure_collection()

        # sample_chunks don't have embeddings
        count = test_indexer.upsert_chunks(sample_chunks)

        assert count == 0

    def test_upsert_empty_list(self, test_indexer):
        """Test upserting empty list."""
        test_indexer.ensure_collection()

        count = test_indexer.upsert_chunks([])

        assert count == 0


@pytest.mark.integration
@pytest.mark.slow
class TestLargeBatchUpsert:
    """Test large batch upsert operations."""

    def test_upsert_100_chunks(self, test_indexer, embedder):
        """Test upserting 100 chunks in batches."""
        from src.models import Chunk, ChunkMetadata

        test_indexer.ensure_collection()

        # Generate 100 chunks with embeddings
        chunks = []
        text = "测试文本：恰斯卡和派蒙在纳塔的冒险。"
        embedding = embedder.embed_single(text)

        for i in range(100):
            metadata = ChunkMetadata(
                task_id="1600",
                task_name="归途",
                chapter_number=i // 10,
                chapter_title=f"第{i // 10}章",
                scene_order=i,
                chunk_order=0,
                event_order=16000000 + i,
                characters=["恰斯卡", "派蒙"],
            )
            chunk = Chunk(
                id=f"batch_chunk_{i}",
                text=f"{text} 序号 {i}",
                metadata=metadata,
                embedding=embedding,  # Reuse same embedding for speed
            )
            chunks.append(chunk)

        count = test_indexer.upsert_chunks(chunks, batch_size=20)

        assert count == 100

        info = test_indexer.get_collection_info()
        assert info["points_count"] == 100
