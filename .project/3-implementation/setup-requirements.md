# Setup Requirements

> **Note**: Based on `techstack-plan.md` v1.2 (Gemini + Jina + M4 Pro)

## 1. System Requirements

- **OS**: macOS (Apple Silicon M1/M2/M3/M4)
- **Python**: 3.11+
- **Package Manager**: `uv` (Recommended) or `pip`
- **Container Runtime**: Docker Desktop (for Qdrant)

## 2. Environment Variables (`.env`)

Create a `.env` file in the project root:

```bash
# LLM Provider (Google Gemini)
# Get key from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY="your-gemini-api-key-here"

# Vector Database (Qdrant)
QDRANT_URL="http://localhost:6333"

# Optional: LangSmith/Smith (Evaluation)
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY="..."
```

## 3. Python Dependencies

The following packages are required. Use `uv pip install` or `pip install`:

### Core RAG
- `llama-index` (Framework)
- `llama-index-llms-gemini` (LLM Integration)
- `llama-index-embeddings-huggingface` (Local Embedding)
- `llama-index-vector-stores-qdrant` (Vector DB)
- `llama-index-postprocessor-jinaai-rerank` (Reranker integration)
- `google-generativeai` (Gemini SDK)

### Hardware Acceleration (Apple Silicon)
- `torch` (PyTorch with MPS support is default on Mac pip)
- `transformers`
- `sentence-transformers`

### Utilities
- `python-dotenv` (Env var loading)
- `streamlit` (Web UI)
- `watchdog` (For streamlist hot reload)

## 4. External Services Setup

### Qdrant (Vector DB)
Run via Docker:
```bash
docker pull qdrant/qdrant
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

## 5. Verification Steps
1. **Verify MPS**: Run python -> `import torch; print(torch.backends.mps.is_available())`. Should be `True`.
2. **Verify Gemini**: Run a simple curl or script to check API key validity.
3. **Verify Qdrant**: Access `http://localhost:6333/dashboard` (if enabled) or `http://localhost:6333`.
