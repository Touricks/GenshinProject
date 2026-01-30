"""Fixtures for Qdrant integration tests."""

import pytest
from typing import List

# Test collection name - isolated from production
TEST_COLLECTION = "test_genshin_story"


def pytest_configure(config):
    """Add custom markers for integration tests."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require Qdrant)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


@pytest.fixture(scope="session")
def qdrant_client():
    """
    Session-scoped Qdrant client.

    Connects to Qdrant on localhost:6333.
    Cleans up test collection after all tests complete.
    """
    from qdrant_client import QdrantClient

    client = QdrantClient(host="localhost", port=6333)

    # Verify connection
    try:
        client.get_collections()
    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")

    yield client

    # Cleanup: delete test collection
    try:
        client.delete_collection(TEST_COLLECTION)
    except Exception:
        pass


@pytest.fixture
def test_indexer(qdrant_client):
    """
    Fresh VectorIndexer with test collection.

    Creates a new indexer for each test.
    Cleans up the collection after the test.
    """
    from src.ingestion.indexer import VectorIndexer

    indexer = VectorIndexer(collection_name=TEST_COLLECTION)

    yield indexer

    # Cleanup after each test
    try:
        indexer.delete_collection()
    except Exception:
        pass


@pytest.fixture(scope="session")
def embedder():
    """
    Session-scoped embedder.

    Downloads BGE model on first run (~400MB).
    Subsequent runs use cached model from ~/.cache/huggingface/
    """
    from src.ingestion.embedder import EmbeddingGenerator

    return EmbeddingGenerator()


@pytest.fixture
def sample_chunk_metadata():
    """Create sample ChunkMetadata for testing."""
    from src.models import ChunkMetadata

    return ChunkMetadata(
        task_id="1600",
        task_name="归途",
        chapter_number=0,
        chapter_title="墟火",
        series_name="空月之歌",
        scene_title="场景一",
        scene_order=1,
        chunk_order=0,
        event_order=16000010,
        characters=["恰斯卡", "派蒙", "伊法"],
        has_choice=False,
        source_file="Data/1600/chapter0_dialogue.txt",
    )


@pytest.fixture
def sample_chunks(sample_chunk_metadata) -> List:
    """Create sample chunks without embeddings."""
    from src.models import Chunk, ChunkMetadata

    texts = [
        "恰斯卡：就在附近。伤口已经处理完了。\n\n派蒙：太好了！",
        "伊法：嗯，好在恰斯卡送医及时。\n\n玩家：伊法刚才是在「看病」吗？",
        "派蒙：况且我们再过不久，就要出发去挪德卡莱了吧？",
        "希诺宁：她是回声之子的先祖，纳塔最初的「六英杰」之一。",
        "基尼奇：阿乔，小声点。\n\n阿乔：知道啦知道啦。",
    ]

    chunks = []
    for i, text in enumerate(texts):
        metadata = ChunkMetadata(
            task_id="1600",
            task_name="归途",
            chapter_number=0,
            chapter_title="墟火",
            series_name="空月之歌",
            scene_title=f"场景{i+1}",
            scene_order=i + 1,
            chunk_order=0,
            event_order=16000010 + i,
            characters=["恰斯卡", "派蒙"] if i < 3 else ["希诺宁", "基尼奇"],
            has_choice=False,
            source_file="Data/1600/chapter0_dialogue.txt",
        )
        chunks.append(Chunk(id=f"chunk_{i}", text=text, metadata=metadata))

    return chunks


@pytest.fixture
def sample_chunks_with_embeddings(sample_chunks, embedder) -> List:
    """Create sample chunks with real BGE embeddings."""
    for chunk in sample_chunks:
        chunk.embedding = embedder.embed_single(chunk.text)
    return sample_chunks


@pytest.fixture
def indexed_test_collection(test_indexer, sample_chunks_with_embeddings):
    """
    Test collection with pre-indexed sample chunks.

    Returns the indexer with data already loaded.
    """
    test_indexer.ensure_collection()
    test_indexer.upsert_chunks(sample_chunks_with_embeddings)
    return test_indexer
