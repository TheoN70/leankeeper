"""
LeanKeeper — Embedding generation.

Uses sentence-transformers to generate embeddings locally.
"""

import logging
import os

logger = logging.getLogger(__name__)

# Suppress noisy logs from dependencies
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)

_model_cache = {}


class Embedder:
    def __init__(self, model_name: str):
        if model_name not in _model_cache:
            # Use cached model without online checks after first download
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {model_name}")
            _model_cache[model_name] = SentenceTransformer(model_name)
        self.model = _model_cache[model_name]
        self.dimension = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        return self.model.encode(texts, show_progress_bar=False).tolist()

    def embed_one(self, text: str) -> list[float]:
        """Embed a single text."""
        return self.model.encode([text])[0].tolist()
