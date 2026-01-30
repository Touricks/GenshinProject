"""Integration tests for EmbeddingGenerator."""

import pytest


@pytest.mark.integration
@pytest.mark.slow
class TestEmbeddingModelLoading:
    """Test BGE model loading from HuggingFace."""

    def test_model_loads(self, embedder):
        """Test that BGE model loads successfully."""
        # Accessing embed_model triggers loading
        model = embedder.embed_model
        assert model is not None

    def test_model_name(self, embedder):
        """Test model name is correct."""
        assert "bge" in embedder.model_name.lower()


@pytest.mark.integration
@pytest.mark.slow
class TestEmbeddingDimension:
    """Test embedding vector dimensions."""

    def test_embedding_dimension_property(self, embedder):
        """Test embedding_dim property returns 768."""
        assert embedder.embedding_dim == 768

    def test_single_embedding_dimension(self, embedder):
        """Test actual embedding has correct dimension."""
        text = "测试文本"
        embedding = embedder.embed_single(text)

        assert len(embedding) == 768

    def test_batch_embedding_dimension(self, embedder):
        """Test batch embeddings have correct dimension."""
        texts = ["文本一", "文本二", "文本三"]
        embeddings = embedder.embed_texts(texts, show_progress=False)

        assert len(embeddings) == 3
        for emb in embeddings:
            assert len(emb) == 768


@pytest.mark.integration
@pytest.mark.slow
class TestChineseTextEmbedding:
    """Test Chinese text embedding quality."""

    def test_chinese_text_embeds(self, embedder):
        """Test that Chinese text produces valid embeddings."""
        text = "恰斯卡是花羽会的族长，精通弓术和飞行。"
        embedding = embedder.embed_single(text)

        assert len(embedding) == 768
        # Check values are normalized (BGE outputs normalized vectors)
        import math
        norm = math.sqrt(sum(x**2 for x in embedding))
        assert 0.99 < norm < 1.01  # Should be approximately 1

    def test_similar_texts_have_high_similarity(self, embedder):
        """Test that similar texts have high cosine similarity."""
        text1 = "恰斯卡是纳塔花羽会的族长"
        text2 = "花羽会由恰斯卡担任族长"
        text3 = "派蒙是旅行者的向导"  # Different topic

        emb1 = embedder.embed_single(text1)
        emb2 = embedder.embed_single(text2)
        emb3 = embedder.embed_single(text3)

        def cosine_similarity(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x**2 for x in a) ** 0.5
            norm_b = sum(x**2 for x in b) ** 0.5
            return dot / (norm_a * norm_b)

        sim_12 = cosine_similarity(emb1, emb2)
        sim_13 = cosine_similarity(emb1, emb3)

        # Similar texts should have higher similarity
        assert sim_12 > sim_13

    def test_empty_text_handling(self, embedder):
        """Test handling of empty text."""
        embedding = embedder.embed_single("")

        # Should still return valid embedding
        assert len(embedding) == 768


@pytest.mark.integration
@pytest.mark.slow
class TestBatchEmbedding:
    """Test batch embedding operations."""

    def test_batch_embed_multiple(self, embedder):
        """Test batch embedding multiple texts."""
        texts = [
            "恰斯卡和伊法是好朋友",
            "派蒙喜欢吃东西",
            "纳塔是火之国度",
            "希诺宁精通机关技术",
            "基尼奇的龙伙伴叫阿乔",
        ]

        embeddings = embedder.embed_texts(texts, show_progress=False)

        assert len(embeddings) == 5

    def test_batch_embed_empty_list(self, embedder):
        """Test batch embedding empty list."""
        embeddings = embedder.embed_texts([], show_progress=False)

        assert embeddings == []

    def test_batch_embed_single_item(self, embedder):
        """Test batch embedding with single item."""
        texts = ["单个文本"]
        embeddings = embedder.embed_texts(texts, show_progress=False)

        assert len(embeddings) == 1
        assert len(embeddings[0]) == 768
