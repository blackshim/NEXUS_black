"""Chunker factory."""

from .base import BaseChunker
from .semantic_chunker import SemanticChunker, ParentChildChunker


def get_chunker(config: dict) -> BaseChunker:
    """Return a chunker based on configuration."""
    strategy = config.get("strategy", "semantic")
    if strategy == "parent_child":
        return ParentChildChunker(config)
    # semantic or other
    return SemanticChunker(config)
