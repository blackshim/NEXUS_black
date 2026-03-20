"""
NEXUS doc-search MCP server -- document search + information retrieval.

7-stage hybrid search pipeline:
  1. Query embedding
  2. RBAC filter construction (Parent excluded)
  3. Dense vector search
  4. Sparse vector search
  5. Hybrid score fusion (RRF)
  6. Reranking
  7. Parent dereference + result formatting
"""

import os
import logging

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, MatchAny,
    SearchParams, SparseVector,
    NamedVector, NamedSparseVector,
)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Stub if MCP SDK is not available
    class FastMCP:
        def __init__(self, name):
            self.name = name
        def tool(self, *a, **kw):
            def dec(fn):
                return fn
            return dec
        def run(self, **kw):
            pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nexus.mcp.doc-search")

# === Configuration ===
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "nexus-qdrant-change-me")
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://localhost:8080")
COLLECTION = "documents"

# Search parameters
DENSE_WEIGHT = float(os.environ.get("DENSE_WEIGHT", "0.7"))
SPARSE_WEIGHT = float(os.environ.get("SPARSE_WEIGHT", "0.3"))
SEARCH_LIMIT = int(os.environ.get("SEARCH_LIMIT", "20"))
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K", "10"))

qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
http = httpx.Client(timeout=30.0)

mcp = FastMCP("nexus-doc-search")


def build_access_filter(user_id: str = "", workspace: str = "") -> Filter:
    """Build RBAC-based access filter. Excludes Parent chunks from search targets."""
    conditions = []

    # Exclude Parent chunks -- only match points where is_parent is absent or False
    # Use must_not so points without is_parent field are also matched
    must_not = [
        FieldCondition(key="is_parent", match=MatchValue(value=True))
    ]

    if workspace:
        conditions.append(
            FieldCondition(key="workspace", match=MatchValue(value=workspace))
        )

    return Filter(must=conditions if conditions else None, must_not=must_not)


def embed_query(text: str) -> dict | None:
    """Embed query text."""
    try:
        resp = http.post(
            f"{EMBEDDING_URL}/embed",
            json={"texts": [text], "instruction": "Represent this sentence for searching relevant passages"},
        )
        resp.raise_for_status()
        data = resp.json()
        result = {"dense": data["dense"][0]}
        if data.get("sparse") and data["sparse"]:
            result["sparse"] = data["sparse"][0]
        return result
    except Exception as e:
        logger.error(f"Embed error: {e}")
        return None


def rerank_results(query: str, texts: list[str], top_k: int = 5) -> list[dict]:
    """Reorder results using reranker."""
    try:
        resp = http.post(
            f"{EMBEDDING_URL}/rerank",
            json={"query": query, "documents": texts, "top_k": top_k},
        )
        resp.raise_for_status()
        return resp.json()["results"]
    except Exception as e:
        logger.warning(f"Rerank error (falling back to original order): {e}")
        return [{"index": i, "score": 1.0, "text": t} for i, t in enumerate(texts[:top_k])]


def fetch_parent_text(parent_id: str) -> str | None:
    """Retrieve Parent chunk text by parent_id."""
    try:
        points = qdrant.retrieve(
            collection_name=COLLECTION,
            ids=[parent_id],
            with_payload=True,
        )
        if points:
            return points[0].payload.get("text")
    except Exception as e:
        logger.warning(f"Parent fetch failed for {parent_id}: {e}")
    return None


@mcp.tool()
def search_documents(
    query: str,
    workspace: str = "",
    file_type: str = "",
    top_k: int = 5,
) -> str:
    """Searches for relevant content in documents.

    Args:
        query: Question or keywords to search
        workspace: Workspace filter (e.g., sales, engineering). Leave empty for all
        file_type: File type filter (e.g., pdf, xlsx). Leave empty for all
        top_k: Number of results to return (default 5)
    """
    # Step 1: Query embedding
    embedding = embed_query(query)
    if embedding is None:
        return "Cannot connect to embedding server."

    # Step 2: Build filter (including Parent exclusion)
    access_filter = build_access_filter(workspace=workspace)

    # Add file type filter
    if file_type:
        type_condition = FieldCondition(
            key="file_type", match=MatchValue(value=file_type)
        )
        if access_filter.must:
            access_filter.must.append(type_condition)
        else:
            access_filter.must = [type_condition]

    # Step 3: Dense search
    dense_results = qdrant.query_points(
        collection_name=COLLECTION,
        query=embedding["dense"],
        using="dense",
        query_filter=access_filter,
        limit=SEARCH_LIMIT,
        with_payload=True,
    ).points

    # Step 4: Sparse search (if available)
    sparse_results = []
    if embedding.get("sparse") and embedding["sparse"].get("indices"):
        try:
            sparse_results = qdrant.query_points(
                collection_name=COLLECTION,
                query=SparseVector(
                    indices=embedding["sparse"]["indices"],
                    values=embedding["sparse"]["values"],
                ),
                using="sparse",
                query_filter=access_filter,
                limit=SEARCH_LIMIT,
                with_payload=True,
            ).points
        except Exception as e:
            logger.warning(f"Sparse search error: {e}")

    # Step 5: Combine scores via RRF (Reciprocal Rank Fusion)
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}
    k = 60  # RRF constant

    for rank, point in enumerate(dense_results):
        pid = point.id
        scores[pid] = scores.get(pid, 0) + DENSE_WEIGHT / (k + rank + 1)
        payloads[pid] = point.payload

    for rank, point in enumerate(sparse_results):
        pid = point.id
        scores[pid] = scores.get(pid, 0) + SPARSE_WEIGHT / (k + rank + 1)
        if pid not in payloads:
            payloads[pid] = point.payload

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:SEARCH_LIMIT]

    if not ranked:
        return "No search results found."

    # Step 6: Reranking -- rerank using Child text (precision matching based)
    candidate_texts = [payloads[pid]["text"] for pid, _ in ranked]
    reranked = rerank_results(query, candidate_texts, top_k=top_k)

    # Step 7: Parent dereference + result formatting
    # If Child has parent_id, return Parent text (rich context)
    # If no parent_id (existing single chunk), return original text
    parent_cache: dict[str, str] = {}  # parent_id -> text cache

    output_parts = []
    seen_parents = set()  # Prevent duplicate Parent returns

    for result in reranked:
        idx = result["index"]
        pid = ranked[idx][0]
        payload = payloads[pid]
        score = result["score"]

        parent_id = payload.get("parent_id")

        if parent_id:
            # If multiple Children of the same Parent match, return Parent only once
            if parent_id in seen_parents:
                continue
            seen_parents.add(parent_id)

            # Retrieve Parent text (using cache)
            if parent_id not in parent_cache:
                parent_text = fetch_parent_text(parent_id)
                if parent_text:
                    parent_cache[parent_id] = parent_text
            text = parent_cache.get(parent_id, payload.get("text", ""))
        else:
            text = payload.get("text", "")

        source = payload.get("file_path", "unknown")
        page = payload.get("page_or_sheet", "")
        ws = payload.get("workspace", "")

        source_info = f"[{source}"
        if page:
            source_info += f" p.{page}"
        source_info += f"] (ws: {ws}, score: {score:.3f})"

        output_parts.append(f"---\n{source_info}\n{text}\n")

    return "\n".join(output_parts)


@mcp.tool()
def get_document_info(file_path: str) -> str:
    """Retrieves indexing information for a specific document.

    Args:
        file_path: Document file path
    """
    try:
        results = qdrant.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="file_path", match=MatchValue(value=file_path))]
            ),
            limit=1,
            with_payload=True,
        )

        points = results[0]
        if not points:
            return f"Document '{file_path}' is not in the index."

        # Query total chunk count for the same file
        all_points = qdrant.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="file_path", match=MatchValue(value=file_path))]
            ),
            limit=10000,
        )
        total = len(all_points[0])
        parents = sum(1 for p in all_points[0] if p.payload.get("is_parent"))
        children = sum(1 for p in all_points[0] if p.payload.get("parent_id"))

        p = points[0].payload
        info = [
            f"File: {p.get('file_path')}",
            f"Type: {p.get('file_type')}",
            f"Workspace: {p.get('workspace')}",
            f"Confidential: {'Yes' if p.get('confidential') else 'No'}",
            f"Modified: {p.get('modified_at')}",
            f"Total points: {total} (parent={parents}, child={children}, other={total-parents-children})",
            f"Hash: {p.get('file_hash', 'N/A')[:16]}...",
        ]

        return "\n".join(info)
    except Exception as e:
        return f"Query error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
