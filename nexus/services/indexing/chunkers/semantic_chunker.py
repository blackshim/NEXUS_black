"""Semantic chunker -- token-based sliding window + Parent-Child Chunking."""

import logging
import uuid

import tiktoken

from .base import BaseChunker, Chunk
from parsers.base import ParsedDocument

logger = logging.getLogger("nexus.chunker.semantic")


class SemanticChunker(BaseChunker):
    """Token-based semantic chunk splitting.

    - Body text: split by chunk_size tokens, with overlap tokens overlapping
    - Tables: separated as individual chunks (to prevent splitting)
    """

    def __init__(self, config: dict):
        self.chunk_size = config.get("chunk_size_tokens", 1536)
        self.overlap = config.get("overlap_tokens", 256)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def chunk(self, parsed: ParsedDocument) -> list[Chunk]:
        chunks = []
        chunk_idx = 0

        for page in parsed.pages:
            # 1. Tables as separate chunks
            if page.tables:
                for table_text in page.tables:
                    if table_text.strip():
                        chunks.append(Chunk(
                            text=table_text.strip(),
                            metadata={
                                "page_or_sheet": page.page_or_sheet,
                                "chunk_type": "table",
                                "chunk_index": chunk_idx,
                            }
                        ))
                        chunk_idx += 1

            # 2. Body text chunk splitting
            text = page.text
            if not text or not text.strip():
                continue

            tokens = self.tokenizer.encode(text)

            if len(tokens) <= self.chunk_size:
                # If within chunk size, keep as-is
                chunks.append(Chunk(
                    text=text.strip(),
                    metadata={
                        "page_or_sheet": page.page_or_sheet,
                        "chunk_type": "text",
                        "chunk_index": chunk_idx,
                    }
                ))
                chunk_idx += 1
            else:
                # Sliding window
                start = 0
                while start < len(tokens):
                    end = min(start + self.chunk_size, len(tokens))
                    chunk_tokens = tokens[start:end]
                    chunk_text = self.tokenizer.decode(chunk_tokens)

                    if chunk_text.strip():
                        chunks.append(Chunk(
                            text=chunk_text.strip(),
                            metadata={
                                "page_or_sheet": page.page_or_sheet,
                                "chunk_type": "text",
                                "chunk_index": chunk_idx,
                            }
                        ))
                        chunk_idx += 1

                    if end >= len(tokens):
                        break
                    start = end - self.overlap

        logger.info(f"Chunked {parsed.file_path} into {len(chunks)} chunks")
        return chunks


class ParentChildChunker(BaseChunker):
    """Parent-Child dual chunk splitting.

    First creates large Parent chunks (context preservation),
    then subdivides each Parent into small Child chunks (search precision).

    - Search: performed on Child vectors (small for precision)
    - Return: returns Parent text of the Child (large for rich context)
    """

    def __init__(self, config: dict):
        pc_config = config.get("parent_child", {})
        self.parent_size = pc_config.get("parent_size_tokens", 2048)
        self.child_size = pc_config.get("child_size_tokens", 384)
        self.child_overlap = pc_config.get("child_overlap_tokens", 64)
        # Keep existing semantic chunker parameters as fallback
        self.chunk_size = config.get("chunk_size_tokens", 1536)
        self.overlap = config.get("overlap_tokens", 256)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def chunk(self, parsed: ParsedDocument) -> list[Chunk]:
        chunks = []
        chunk_idx = 0

        for page in parsed.pages:
            # 1. Tables as separate chunks (Parent-Child not applied, must not be split)
            if page.tables:
                for table_text in page.tables:
                    if table_text.strip():
                        chunks.append(Chunk(
                            text=table_text.strip(),
                            metadata={
                                "page_or_sheet": page.page_or_sheet,
                                "chunk_type": "table",
                                "chunk_index": chunk_idx,
                            }
                        ))
                        chunk_idx += 1

            # 2. Body text -> Parent-Child splitting
            text = page.text
            if not text or not text.strip():
                continue

            tokens = self.tokenizer.encode(text)

            if len(tokens) <= self.child_size:
                # If within Child size, single chunk (Parent-Child unnecessary)
                chunks.append(Chunk(
                    text=text.strip(),
                    metadata={
                        "page_or_sheet": page.page_or_sheet,
                        "chunk_type": "text",
                        "chunk_index": chunk_idx,
                    }
                ))
                chunk_idx += 1
                continue

            # Create Parent chunks (sliding window)
            parent_start = 0
            while parent_start < len(tokens):
                parent_end = min(parent_start + self.parent_size, len(tokens))
                parent_tokens = tokens[parent_start:parent_end]
                parent_text = self.tokenizer.decode(parent_tokens)

                if not parent_text.strip():
                    parent_start = parent_end
                    continue

                parent_id = str(uuid.uuid4())

                # Parent chunk (parent_id also stored in metadata -> worker uses it as Qdrant point_id)
                chunks.append(Chunk(
                    text=parent_text.strip(),
                    metadata={
                        "page_or_sheet": page.page_or_sheet,
                        "chunk_type": "parent",
                        "chunk_index": chunk_idx,
                        "parent_id": parent_id,
                    },
                    is_parent=True,
                ))
                chunk_idx += 1

                # Create Child chunks (subdivide within Parent)
                child_start = 0
                while child_start < len(parent_tokens):
                    child_end = min(child_start + self.child_size, len(parent_tokens))
                    child_tokens = parent_tokens[child_start:child_end]
                    child_text = self.tokenizer.decode(child_tokens)

                    if child_text.strip():
                        chunks.append(Chunk(
                            text=child_text.strip(),
                            metadata={
                                "page_or_sheet": page.page_or_sheet,
                                "chunk_type": "child",
                                "chunk_index": chunk_idx,
                            },
                            parent_id=parent_id,
                        ))
                        chunk_idx += 1

                    if child_end >= len(parent_tokens):
                        break
                    child_start = child_end - self.child_overlap

                # Next Parent (no overlap, contiguous)
                if parent_end >= len(tokens):
                    break
                parent_start = parent_end

        parent_count = sum(1 for c in chunks if c.is_parent)
        child_count = sum(1 for c in chunks if c.parent_id)
        other_count = len(chunks) - parent_count - child_count
        logger.info(
            f"Chunked {parsed.file_path} into {len(chunks)} chunks "
            f"(parents={parent_count}, children={child_count}, other={other_count})"
        )
        return chunks
