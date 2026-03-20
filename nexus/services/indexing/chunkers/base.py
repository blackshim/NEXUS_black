"""Chunker base interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from parsers.base import ParsedDocument


@dataclass
class Chunk:
    """A single chunk.

    Parent-Child Chunking support:
    - is_parent=True: Large chunk for context preservation (not a search target, used for text return)
    - is_parent=False + parent_id present: Small chunk for search (Child)
    - is_parent=False + parent_id absent: Existing single chunk (semantic strategy)
    """
    text: str
    metadata: dict = field(default_factory=dict)
    # Keys included in metadata: page_or_sheet, chunk_type (text/table), chunk_index
    parent_id: str | None = None   # Child -> Parent reference ID
    is_parent: bool = False        # True means Parent chunk (not a search target)


class BaseChunker(ABC):
    """Base class for all chunkers."""

    @abstractmethod
    def chunk(self, parsed: ParsedDocument) -> list[Chunk]:
        """Split a ParsedDocument into a list of chunks."""
        ...
