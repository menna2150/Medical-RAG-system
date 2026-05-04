import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:
    """Sentence-BioBERT wrapper. Returns L2-normalized vectors so that
    inner-product search in FAISS = cosine similarity."""

    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vecs.astype("float32")
