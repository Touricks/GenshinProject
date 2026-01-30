"""End-to-end integration tests for the full pipeline."""

import pytest
from pathlib import Path


@pytest.mark.integration
@pytest.mark.slow
class TestPipelineEndToEnd:
    """End-to-end tests for the full ingestion pipeline."""

    def test_full_pipeline_single_file(self, test_indexer, embedder):
        """Test full pipeline with a single dialogue file."""
        from src.ingestion.loader import DocumentLoader
        from src.ingestion.chunker import SceneChunker
        from src.ingestion.enricher import MetadataEnricher, create_chunks_from_document

        # Check if Data directory exists
        data_dir = Path("Data")
        if not data_dir.exists():
            pytest.skip("Data directory not found")

        # Find a test file
        test_files = list(data_dir.glob("*/chapter0_dialogue.txt"))
        if not test_files:
            pytest.skip("No test files found")

        test_file = test_files[0]
        task_id = test_file.parent.name

        # Step 1: Load document
        loader = DocumentLoader(data_dir)
        documents = list(loader._load_task(test_file.parent))
        assert len(documents) >= 1

        document = documents[0]

        # Step 2: Chunk document
        chunker = SceneChunker()
        enricher = MetadataEnricher()
        chunks = create_chunks_from_document(document, chunker, enricher)
        assert len(chunks) > 0

        # Step 3: Generate embeddings
        for chunk in chunks[:10]:  # Limit to 10 for speed
            chunk.embedding = embedder.embed_single(chunk.text)

        chunks_with_embeddings = [c for c in chunks[:10] if c.embedding]
        assert len(chunks_with_embeddings) > 0

        # Step 4: Index to Qdrant
        test_indexer.ensure_collection()
        count = test_indexer.upsert_chunks(chunks_with_embeddings)
        assert count == len(chunks_with_embeddings)

        # Step 5: Verify with search
        query = chunks_with_embeddings[0].text[:50]
        query_vector = embedder.embed_single(query)
        results = test_indexer.search(query_vector, limit=1)

        assert len(results) == 1
        assert results[0]["payload"]["task_id"] == task_id

    def test_pipeline_filter_by_task_after_indexing(self, test_indexer, embedder):
        """Test filtering by task_id after indexing multiple tasks."""
        from src.models import Chunk, ChunkMetadata

        test_indexer.ensure_collection()

        # Create chunks from two different tasks
        chunks = []
        for task_id in ["1600", "1601"]:
            for i in range(3):
                metadata = ChunkMetadata(
                    task_id=task_id,
                    task_name=f"任务{task_id}",
                    chapter_number=0,
                    chapter_title="测试章节",
                    scene_order=i,
                    chunk_order=0,
                    event_order=int(task_id) * 10000 + i,
                    characters=["测试角色"],
                )
                text = f"任务 {task_id} 的测试文本 {i}"
                chunk = Chunk(
                    id=f"{task_id}_{i}",
                    text=text,
                    metadata=metadata,
                    embedding=embedder.embed_single(text),
                )
                chunks.append(chunk)

        test_indexer.upsert_chunks(chunks)

        # Search with task_id filter
        query_vector = embedder.embed_single("测试文本")

        results_1600 = test_indexer.search(
            query_vector, limit=10, filter_conditions={"task_id": "1600"}
        )
        results_1601 = test_indexer.search(
            query_vector, limit=10, filter_conditions={"task_id": "1601"}
        )

        assert len(results_1600) == 3
        assert len(results_1601) == 3

        for r in results_1600:
            assert r["payload"]["task_id"] == "1600"
        for r in results_1601:
            assert r["payload"]["task_id"] == "1601"


@pytest.mark.integration
class TestPipelineDryRun:
    """Test pipeline dry-run mode."""

    def test_dry_run_no_qdrant_write(self):
        """Test that dry-run mode doesn't write to Qdrant."""
        from src.ingestion.pipeline import IngestionPipeline
        from pathlib import Path

        data_dir = Path("Data")
        if not data_dir.exists():
            pytest.skip("Data directory not found")

        # Run pipeline in dry-run mode
        pipeline = IngestionPipeline(
            data_dir=data_dir,
            collection_name="test_dry_run_collection",
        )

        stats = pipeline.run(dry_run=True)

        # Should process documents but not index
        assert stats.documents_processed > 0
        assert stats.chunks_created > 0
        assert stats.chunks_indexed == 0  # Dry-run doesn't index


@pytest.mark.integration
@pytest.mark.slow
class TestPipelineErrorHandling:
    """Test pipeline error handling."""

    def test_invalid_data_directory(self):
        """Test handling of invalid data directory."""
        from src.ingestion.loader import DocumentLoader

        with pytest.raises(ValueError, match="not found"):
            DocumentLoader(Path("/nonexistent/path"))

    def test_chunk_without_embedding_skipped(self, test_indexer):
        """Test that chunks without embeddings are skipped gracefully."""
        from src.models import Chunk, ChunkMetadata

        test_indexer.ensure_collection()

        # Create chunk without embedding
        metadata = ChunkMetadata(
            task_id="1600",
            task_name="测试",
            chapter_number=0,
            chapter_title="测试",
            scene_order=0,
            chunk_order=0,
            event_order=16000000,
            characters=[],
        )
        chunk = Chunk(id="no_embedding", text="测试文本", metadata=metadata)

        # Should skip without error
        count = test_indexer.upsert_chunks([chunk])
        assert count == 0
