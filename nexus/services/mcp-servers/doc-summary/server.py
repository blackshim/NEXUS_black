"""
NEXUS doc-summary MCP server -- document summarization.

Tools:
- summarize_document: Retrieves full content of a specific file for summarization
- summarize_topic: Searches by topic and provides comprehensive content for summarization
"""

import os
import logging

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    class FastMCP:
        def __init__(self, name): self.name = name
        def tool(self, *a, **kw):
            def dec(fn): return fn
            return dec
        def run(self, **kw): pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nexus.mcp.doc-summary")

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "nexus-qdrant-change-me")
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://localhost:8080")
COLLECTION = "documents"

qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
http = httpx.Client(timeout=30.0)

mcp = FastMCP("nexus-doc-summary")


def _get_all_chunks(file_path: str) -> list[dict]:
    """Retrieve all chunks of a file from Qdrant."""
    results = qdrant.scroll(
        collection_name=COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="file_path", match=MatchValue(value=file_path))]
        ),
        limit=10000,
        with_payload=True,
    )
    points = results[0]
    # Sort by chunk_index
    points.sort(key=lambda p: p.payload.get("chunk_index", 0))
    return [{"text": p.payload.get("text", ""), "page": p.payload.get("page_or_sheet", "")} for p in points]


def _search_chunks(query: str, limit: int = 10) -> list[dict]:
    """Search for related chunks by query."""
    # Embedding
    resp = http.post(
        f"{EMBEDDING_URL}/embed",
        json={"texts": [query], "instruction": "Represent this sentence for searching relevant passages"},
    )
    resp.raise_for_status()
    emb = resp.json()

    # Dense search
    from qdrant_client.models import SparseVector
    results = qdrant.query_points(
        collection_name=COLLECTION,
        query=emb["dense"][0],
        using="dense",
        limit=limit,
        with_payload=True,
    ).points

    return [
        {
            "text": p.payload.get("text", ""),
            "file": p.payload.get("file_path", "").replace("\\", "/").split("/")[-1],
            "page": p.payload.get("page_or_sheet", ""),
            "score": p.score,
        }
        for p in results
    ]


@mcp.tool()
def summarize_document(file_path: str) -> str:
    """Summarizes the full content of a specific document.

    Retrieves all chunks of a document indexed in Qdrant and returns the full content.
    The LLM can generate a summary based on this content.

    Args:
        file_path: Document file path (indexed path)
    """
    chunks = _get_all_chunks(file_path)

    if not chunks:
        # Try partial matching
        all_points = qdrant.scroll(collection_name=COLLECTION, limit=10000, with_payload=["file_path"])
        all_paths = set(p.payload.get("file_path", "") for p in all_points[0])
        matches = [fp for fp in all_paths if file_path.lower() in fp.lower() or fp.split("/")[-1].lower() in file_path.lower()]

        if matches:
            chunks = _get_all_chunks(matches[0])
            file_path = matches[0]

    if not chunks:
        return f"Document '{file_path}' is not in the index."

    # Combine full content
    output = f"[Document: {file_path.split('/')[-1]}] Total {len(chunks)} chunks\n\n"
    for chunk in chunks:
        page_info = f" (p.{chunk['page']})" if chunk['page'] else ""
        output += f"---{page_info}---\n{chunk['text']}\n\n"

    return output


@mcp.tool()
def summarize_topic(topic: str, max_sources: int = 5) -> str:
    """Searches for documents related to a topic and provides content for comprehensive summarization.

    Gathers related content from multiple documents so the LLM can generate a comprehensive summary.

    Args:
        topic: Topic to summarize (e.g., "quality management", "sales strategy")
        max_sources: Maximum number of search sources (default 5)
    """
    chunks = _search_chunks(topic, limit=max_sources * 2)

    if not chunks:
        return f"Could not find documents related to '{topic}'."

    # Group by file
    by_file: dict[str, list[dict]] = {}
    for chunk in chunks:
        fname = chunk["file"]
        if fname not in by_file:
            by_file[fname] = []
        by_file[fname].append(chunk)

    # Top max_sources files only
    top_files = list(by_file.items())[:max_sources]

    output = f"[Topic: {topic}] Related content found in {len(top_files)} documents\n\n"
    for fname, file_chunks in top_files:
        output += f"## {fname}\n"
        for chunk in file_chunks:
            page_info = f" (p.{chunk['page']})" if chunk['page'] else ""
            output += f"{chunk['text'][:500]}{page_info}\n\n"

    output += "---\nPlease generate a comprehensive summary based on the above content."

    return output


if __name__ == "__main__":
    mcp.run(transport="stdio")
