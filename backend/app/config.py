from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    embedding_model: str = "pritamdeka/S-BioBert-snli-multinli-stsb"
    index_dir: str = "./data/index"
    top_k: int = 8
    min_retrieval_score: float = 0.30

    # Hybrid retrieval (dense + BM25 + RRF)
    retrieve_fanout: int = 30
    rrf_k: int = 60

    # Cross-encoder reranker. Empty string disables it.
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_pool: int = 20

    allowed_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    @property
    def index_path(self) -> Path:
        return Path(self.index_dir)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
