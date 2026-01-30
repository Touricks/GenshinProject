"""Shared fixtures for extraction tests."""

import json
import pytest
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "Data"
EVAL_DIR = PROJECT_ROOT / "evaluation" / "extraction"


# =============================================================================
# Dataset Loading Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def chunking_dataset():
    """Load chunking evaluation dataset."""
    with open(EVAL_DIR / "chunking_eval.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def metadata_dataset():
    """Load metadata evaluation dataset."""
    with open(EVAL_DIR / "metadata_eval.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def entity_dataset():
    """Load entity evaluation dataset."""
    with open(EVAL_DIR / "entity_eval.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def relationship_dataset():
    """Load relationship evaluation dataset."""
    with open(EVAL_DIR / "relationship_eval.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def resolution_dataset():
    """Load resolution evaluation dataset."""
    with open(EVAL_DIR / "resolution_eval.json", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_chapter_content():
    """Load sample chapter content for testing."""
    chapter_file = DATA_DIR / "1600" / "chapter0_dialogue.txt"
    if chapter_file.exists():
        return chapter_file.read_text(encoding="utf-8")
    pytest.skip("Sample data file not found")


@pytest.fixture
def sample_dialogue_text():
    """Sample dialogue text for unit tests."""
    return """## 与恰斯卡对话

伊法：…伤口已经处理完了。所以你是在哪发现的它？怎么会伤成这样？

恰斯卡：就在附近的海滩上，还是那些家伙干的…

派蒙：——嘿！恰斯卡，你们围在这做什么呢？

恰斯卡：嗯，派蒙？还有我们的「杜麦尼」？

伊法：「杜麦尼」？派蒙？好久不见。"""


@pytest.fixture
def sample_choice_text():
    """Sample choice block for testing."""
    return """## 选项
- 想再多陪陪朋友。
- 想打发一下时间。

玩家：想再多陪陪朋友。

恰斯卡：呵…这么一说，确实很久没跟你们一起作战了。"""


@pytest.fixture
def sample_anonymous_text():
    """Sample text with anonymous speaker."""
    return """？？？：稍早之前…

？？？：……

？？？：…在哪里…

？？？：…要…找到…他们…

小机器人：滴…滴…嘟…"""


@pytest.fixture
def sample_header_text():
    """Sample chapter header for parsing tests."""
    return """# 归途 - 第0章：墟火
# 空月之歌 序奏
# 来源：https://gi.yatta.moe/chs/archive/quest/1602/the-journey-home?chapter=0

## 剧情简介
纳塔似乎迎来了一些意料之外的客人…"""


# =============================================================================
# Pipeline Component Fixtures
# =============================================================================


@pytest.fixture
def document_loader():
    """Create a DocumentLoader instance."""
    from src.ingestion.loader import DocumentLoader
    return DocumentLoader(DATA_DIR)


@pytest.fixture
def scene_chunker():
    """Create a SceneChunker instance."""
    from src.ingestion.chunker import SceneChunker
    return SceneChunker()


@pytest.fixture
def metadata_enricher():
    """Create a MetadataEnricher instance."""
    from src.ingestion.enricher import MetadataEnricher
    return MetadataEnricher()


# =============================================================================
# Utility Functions
# =============================================================================


def get_test_cases_by_category(dataset: dict, category: str) -> list:
    """Filter test cases by category."""
    return [item for item in dataset.get("items", []) if item.get("category") == category]


def get_test_cases_by_difficulty(dataset: dict, difficulty: str) -> list:
    """Filter test cases by difficulty."""
    return [item for item in dataset.get("items", []) if item.get("difficulty") == difficulty]


def get_test_cases_by_layer(dataset: dict, layer: str) -> list:
    """Filter test cases by layer (for entity/relationship datasets)."""
    return [item for item in dataset.get("items", []) if item.get("layer") == layer]


# =============================================================================
# Metrics Calculation
# =============================================================================


def calculate_f1(predicted: set, expected: set) -> float:
    """Calculate F1 score."""
    if not predicted and not expected:
        return 1.0
    if not predicted or not expected:
        return 0.0

    true_positives = len(predicted & expected)
    precision = true_positives / len(predicted) if predicted else 0
    recall = true_positives / len(expected) if expected else 0

    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def calculate_accuracy(correct: int, total: int) -> float:
    """Calculate accuracy."""
    if total == 0:
        return 1.0
    return correct / total


# =============================================================================
# Pytest Markers
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "vector: marks tests for vector DB extraction")
    config.addinivalue_line("markers", "graph: marks tests for graph DB extraction")
    config.addinivalue_line("markers", "llm: marks tests that require LLM API access (skip with '-m \"not llm\"')")
