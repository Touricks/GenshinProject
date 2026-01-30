"""Integration tests for vector search functionality."""

import pytest


@pytest.mark.integration
@pytest.mark.slow
class TestBasicSearch:
    """Test basic vector similarity search."""

    def test_basic_search(self, indexed_test_collection, embedder):
        """Test basic vector search returns results."""
        query = "恰斯卡处理伤口"
        query_vector = embedder.embed_single(query)

        results = indexed_test_collection.search(query_vector, limit=3)

        assert len(results) > 0
        assert len(results) <= 3

    def test_search_returns_payload(self, indexed_test_collection, embedder):
        """Test search results include payload data."""
        query = "派蒙说话"
        query_vector = embedder.embed_single(query)

        results = indexed_test_collection.search(query_vector, limit=1)

        assert len(results) == 1
        result = results[0]

        assert "id" in result
        assert "score" in result
        assert "payload" in result

        payload = result["payload"]
        assert "text" in payload
        assert "task_id" in payload
        assert "characters" in payload

    def test_search_scores_ordered(self, indexed_test_collection, embedder):
        """Test search results are ordered by score descending."""
        query = "恰斯卡"
        query_vector = embedder.embed_single(query)

        results = indexed_test_collection.search(query_vector, limit=5)

        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.integration
@pytest.mark.slow
class TestFilteredSearch:
    """Test search with filter conditions."""

    def test_filter_by_task_id(self, indexed_test_collection, embedder):
        """Test filtering by task_id."""
        query = "对话"
        query_vector = embedder.embed_single(query)

        results = indexed_test_collection.search(
            query_vector,
            limit=10,
            filter_conditions={"task_id": "1600"},
        )

        for result in results:
            assert result["payload"]["task_id"] == "1600"

    def test_filter_by_chapter(self, indexed_test_collection, embedder):
        """Test filtering by chapter_number."""
        query = "对话"
        query_vector = embedder.embed_single(query)

        results = indexed_test_collection.search(
            query_vector,
            limit=10,
            filter_conditions={"chapter_number": 0},
        )

        for result in results:
            assert result["payload"]["chapter_number"] == 0

    def test_filter_no_results(self, indexed_test_collection, embedder):
        """Test filter that returns no results."""
        query = "对话"
        query_vector = embedder.embed_single(query)

        results = indexed_test_collection.search(
            query_vector,
            limit=10,
            filter_conditions={"task_id": "9999"},  # Non-existent
        )

        assert len(results) == 0


@pytest.mark.integration
@pytest.mark.slow
class TestSearchRelevance:
    """Test search result relevance."""

    def test_relevant_query_finds_character(self, indexed_test_collection, embedder):
        """Test that character-specific query finds relevant chunks."""
        # Query about 恰斯卡
        query = "恰斯卡处理伤口"
        query_vector = embedder.embed_single(query)

        results = indexed_test_collection.search(query_vector, limit=1)

        assert len(results) == 1
        # Top result should contain 恰斯卡
        assert "恰斯卡" in results[0]["payload"]["text"]

    def test_relevant_query_finds_location(self, indexed_test_collection, embedder):
        """Test that location-specific query finds relevant chunks."""
        # Query about 挪德卡莱
        query = "前往挪德卡莱"
        query_vector = embedder.embed_single(query)

        results = indexed_test_collection.search(query_vector, limit=1)

        assert len(results) == 1
        # Top result should mention 挪德卡莱
        assert "挪德卡莱" in results[0]["payload"]["text"]

    def test_relevant_query_finds_historical_figure(
        self, indexed_test_collection, embedder
    ):
        """Test that historical figure query finds relevant chunks."""
        # Query about 六英杰
        query = "六英杰和回声之子"
        query_vector = embedder.embed_single(query)

        results = indexed_test_collection.search(query_vector, limit=1)

        assert len(results) == 1
        # Top result should mention 六英杰
        assert "六英杰" in results[0]["payload"]["text"]


@pytest.mark.integration
@pytest.mark.slow
class TestSearchEdgeCases:
    """Test search edge cases."""

    def test_search_empty_collection(self, test_indexer, embedder):
        """Test searching an empty collection."""
        test_indexer.ensure_collection()

        query_vector = embedder.embed_single("任意查询")

        results = test_indexer.search(query_vector, limit=5)

        assert len(results) == 0

    def test_search_limit_respected(self, indexed_test_collection, embedder):
        """Test that search limit is respected."""
        query_vector = embedder.embed_single("对话")

        results_1 = indexed_test_collection.search(query_vector, limit=1)
        results_3 = indexed_test_collection.search(query_vector, limit=3)

        assert len(results_1) == 1
        assert len(results_3) == 3
