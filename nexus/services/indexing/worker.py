"""
NEXUS Indexing Worker -- parses files -> chunks -> embeds -> stores in Qdrant.

Processes jobs from Redis queue, or can process files directly.
"""

import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import redis
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

from parsers import get_parser
from chunkers import get_chunker
from utils.config_loader import get_indexing_config, get_embedding_config, get_llm_config
from utils.path_utils import detect_workspace, is_confidential, normalize_path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger("nexus.worker")

# === Environment Variables ===
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "nexus-qdrant-change-me")
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://localhost:8080")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


class IndexingWorker:
    def __init__(self):
        self.qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        self.redis = redis.from_url(REDIS_URL)

        # === Config Load ===
        config = get_indexing_config()
        embedding_config = get_embedding_config()

        # Qdrant settings
        qdrant_config = config.get("qdrant", {})
        self._collection = qdrant_config.get("collection", "documents")
        self._upsert_batch_size = qdrant_config.get("upsert_batch_size", 100)

        # Redis queue settings
        redis_config = config.get("redis", {})
        self._queue_name = redis_config.get("queue_name", "nexus:indexing:queue")
        self._retry_queue = redis_config.get("retry_queue", "nexus:indexing:retry")
        self._dead_letter_queue = redis_config.get("dead_letter_queue", "nexus:indexing:dead_letter")
        self._brpop_timeout = redis_config.get("brpop_timeout", 5)

        # Retry settings
        retry_config = config.get("retry", {})
        self._max_retries = retry_config.get("max_retries", 3)

        # Embedding settings
        self._embedding_batch_size = embedding_config.get("max_batch_size", 32)
        self._dense_dim = embedding_config.get("dense_dim", 1024)

        # Supported extensions (loaded from config)
        self._supported_extensions = set(config.get("supported_extensions", [
            ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".csv",
            ".txt", ".md", ".log", ".json", ".xml", ".yaml", ".yml",
            ".html", ".htm",
        ]))

        # Contextual Chunking settings
        ctx_config = config.get("contextual_chunking", {})
        self._contextual_enabled = ctx_config.get("enabled", False)
        self._context_max_tokens = ctx_config.get("max_context_tokens", 128)

        # HTTP client
        self.http = httpx.Client(timeout=60.0)

        # Initialize Chunker
        chunking_config = config.get("chunking", {}).get("default", {})
        # Merge parent_child config into chunking_config (so factory can access it)
        pc_config = config.get("chunking", {}).get("parent_child", {})
        if pc_config:
            chunking_config["parent_child"] = pc_config
        self.chunker = get_chunker(chunking_config)

        logger.info(f"Worker initialized — Qdrant: {QDRANT_URL}, Embedding: {EMBEDDING_URL}")

    def process_file(self, file_path: str) -> dict:
        """Index a single file. Returns a result summary."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return {"status": "error", "reason": "file_not_found"}

        # 1. File hash check (duplicate prevention)
        file_hash = self._compute_hash(path)
        if self._hash_exists(file_hash):
            logger.info(f"Skip (unchanged): {file_path}")
            return {"status": "skipped", "reason": "unchanged"}

        # 2. Delete existing vectors (on file update)
        self._delete_vectors(file_path)

        # 3. Parse
        parser = get_parser(path)
        if parser is None:
            logger.warning(f"No parser for: {path.suffix}")
            return {"status": "error", "reason": "unsupported_format"}

        try:
            parsed = parser.parse(path)
        except Exception as e:
            logger.error(f"Parse error {file_path}: {e}")
            return {"status": "error", "reason": f"parse_error: {e}"}

        # 4. Chunk splitting
        chunks = self.chunker.chunk(parsed)
        if not chunks:
            logger.warning(f"No chunks from: {file_path}")
            return {"status": "error", "reason": "no_chunks"}

        # 5. Prepare metadata
        workspace = detect_workspace(file_path)
        confidential = is_confidential(file_path)
        norm_path = normalize_path(file_path)
        file_name = path.name
        file_type = path.suffix.lower().lstrip(".")
        modified_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat()
        indexed_at = datetime.now(tz=timezone.utc).isoformat()

        # Language detection (simple: check for Korean characters)
        sample_text = " ".join(c.text[:200] for c in chunks[:3])
        has_korean = any("\uac00" <= ch <= "\ud7a3" for ch in sample_text)
        language = "ko" if has_korean else "en"

        total_chunks = len(chunks)

        # 5.5. Contextual Chunking -- generate LLM context before embedding
        if self._contextual_enabled:
            chunks = self._enrich_chunks_with_context(chunks, file_name)

        # 6. Embedding (batch) -- skip Parent chunks, embed only the rest
        embeddable_chunks = [c for c in chunks if not c.is_parent]
        parent_chunks = [c for c in chunks if c.is_parent]

        embeddings = {}  # chunk index -> embedding
        if embeddable_chunks:
            # Contextual: if context exists, embed "context + original" combined
            texts = []
            for c in embeddable_chunks:
                context = c.metadata.get("context", "")
                if context:
                    texts.append(f"{context}\n\n{c.text}")
                else:
                    texts.append(c.text)
            emb_results = self._embed_batch(texts)
            if emb_results is None:
                return {"status": "error", "reason": "embedding_failed"}
            for chunk, emb in zip(embeddable_chunks, emb_results):
                embeddings[chunk.metadata.get("chunk_index")] = emb

        # 7. Store in Qdrant
        points = []
        zero_vector = [0.0] * self._dense_dim  # Dummy vector for Parent

        for i, chunk in enumerate(chunks):
            # Parent chunk: use chunker-generated parent_id as Qdrant point_id
            # -> Child's parent_id references this point_id for reverse lookup
            if chunk.is_parent:
                point_id = chunk.metadata.get("parent_id", str(uuid.uuid4()))
            else:
                point_id = str(uuid.uuid4())

            payload = {
                "text": chunk.text,
                "file_path": norm_path,
                "file_name": file_name,
                "file_type": file_type,
                "file_hash": file_hash,
                "workspace": workspace,
                "confidential": confidential,
                "modified_at": modified_at,
                "indexed_at": indexed_at,
                "language": language,
                "chunk_index": chunk.metadata.get("chunk_index", i),
                "chunk_type": chunk.metadata.get("chunk_type", "text"),
                "page_or_sheet": str(chunk.metadata.get("page_or_sheet", "")),
                "total_chunks": total_chunks,
                "entities": [],  # Phase 2: entity slot to be filled by GLiNER-ko
            }

            # Parent-Child metadata
            if chunk.is_parent:
                payload["is_parent"] = True
            if chunk.parent_id:
                payload["parent_id"] = chunk.parent_id
            if chunk.metadata.get("context"):
                payload["context"] = chunk.metadata["context"]

            # Add document metadata
            if parsed.metadata:
                if parsed.metadata.get("title"):
                    payload["doc_title"] = parsed.metadata["title"]
                if parsed.metadata.get("author"):
                    payload["doc_author"] = parsed.metadata["author"]

            # Determine vector: Parent -> dummy, others -> actual embedding
            if chunk.is_parent:
                point = PointStruct(
                    id=point_id,
                    vector={"dense": zero_vector},
                    payload=payload,
                )
            else:
                emb = embeddings.get(chunk.metadata.get("chunk_index"))
                if emb is None:
                    continue
                point = PointStruct(
                    id=point_id,
                    vector={"dense": emb["dense"]},
                    payload=payload,
                )
                # Add sparse vector
                if emb.get("sparse") and emb["sparse"]["indices"]:
                    point.vector["sparse"] = emb["sparse"]

            points.append(point)

        # Batch upsert
        for batch_start in range(0, len(points), self._upsert_batch_size):
            batch = points[batch_start : batch_start + self._upsert_batch_size]
            self.qdrant.upsert(collection_name=self._collection, points=batch)

        logger.info(f"Indexed: {file_path} -> {len(points)} vectors (ws={workspace})")

        return {
            "status": "success",
            "file_path": norm_path,
            "chunks": len(points),
            "workspace": workspace,
            "confidential": confidential,
        }

    def _enrich_chunks_with_context(self, chunks: list, file_name: str) -> list:
        """Generate LLM context for each embeddable chunk and store in metadata["context"].

        Parent-Child structure:
        - Child -> provide its Parent text as context
        - Single chunk (no parent_id) -> skip context generation (no Parent to provide context)
        - Parent -> skip (not an embedding target)
        """
        # Parent ID -> text mapping
        parent_texts = {}
        for c in chunks:
            if c.is_parent:
                pid = c.metadata.get("parent_id")
                if pid:
                    parent_texts[pid] = c.text

        if not parent_texts:
            logger.info(f"Contextual chunking skipped for {file_name}: no parent chunks")
            return chunks

        # Load LLM settings
        llm_config = get_llm_config()
        offline = llm_config.get("offline", {})
        endpoint = offline.get("endpoint", "http://localhost:11434")
        model = offline.get("model", "qwen3:4b")
        ollama_url = os.environ.get("OLLAMA_URL", endpoint)
        timeout = offline.get("timeout", 60)
        max_tokens = self._context_max_tokens

        enriched = 0
        for chunk in chunks:
            if chunk.is_parent or not chunk.parent_id:
                continue

            parent_text = parent_texts.get(chunk.parent_id)
            if not parent_text:
                continue

            prompt = (
                f"Below is a section from the document '{file_name}':\n"
                f"---\n{parent_text[:3000]}\n---\n\n"
                f"Explain in one sentence the context of the following chunk within the above document section. "
                f"Include key keywords to aid search. Output only the explanation.\n\n"
                f"Chunk: {chunk.text[:1000]}"
            )

            try:
                with httpx.Client(timeout=float(timeout)) as client:
                    resp = client.post(
                        f"{ollama_url}/api/chat",
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "stream": False,
                            "think": False,
                            "options": {"temperature": 0.1, "num_predict": max_tokens},
                        },
                    )
                    resp.raise_for_status()
                    context = resp.json().get("message", {}).get("content", "").strip()
                    if context:
                        chunk.metadata["context"] = context
                        enriched += 1
            except Exception as e:
                logger.warning(f"Context generation failed for chunk {chunk.metadata.get('chunk_index')}: {e}")

        logger.info(f"Contextual chunking: {enriched}/{len([c for c in chunks if c.parent_id])} children enriched for {file_name}")
        return chunks

    def _embed_batch(self, texts: list[str]) -> list[dict] | None:
        """Convert text to vectors via embedding server."""
        all_embeddings = []

        for i in range(0, len(texts), self._embedding_batch_size):
            batch = texts[i : i + self._embedding_batch_size]
            try:
                resp = self.http.post(
                    f"{EMBEDDING_URL}/embed",
                    json={"texts": batch},
                )
                resp.raise_for_status()
                data = resp.json()

                for j in range(len(batch)):
                    emb = {"dense": data["dense"][j]}
                    if "sparse" in data and j < len(data["sparse"]):
                        emb["sparse"] = data["sparse"][j]
                    all_embeddings.append(emb)
            except Exception as e:
                logger.error(f"Embedding error: {e}")
                return None

        return all_embeddings

    def _delete_vectors(self, file_path: str):
        """Delete existing vectors for a file (on update)."""
        norm_path = normalize_path(file_path)
        try:
            self.qdrant.delete(
                collection_name=self._collection,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="file_path", match=MatchValue(value=norm_path)
                        )
                    ]
                ),
            )
        except Exception as e:
            logger.warning(f"Delete error for {file_path}: {e}")

    def _hash_exists(self, file_hash: str) -> bool:
        """Check if the same hash exists in Qdrant."""
        try:
            result = self.qdrant.scroll(
                collection_name=self._collection,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="file_hash", match=MatchValue(value=file_hash)
                        )
                    ]
                ),
                limit=1,
            )
            return len(result[0]) > 0
        except Exception:
            return False

    def delete_file(self, file_path: str) -> dict:
        """Remove vectors from Qdrant when a file is deleted."""
        norm_path = normalize_path(file_path)
        try:
            # Check vector count before deletion
            before = self.qdrant.scroll(
                collection_name=self._collection,
                scroll_filter=Filter(
                    must=[FieldCondition(key="file_path", match=MatchValue(value=norm_path))]
                ),
                limit=10000,
            )
            count = len(before[0])

            if count == 0:
                logger.info(f"Delete skip (not indexed): {file_path}")
                return {"status": "skipped", "reason": "not_indexed"}

            self._delete_vectors(file_path)
            logger.info(f"Deleted: {file_path} ({count} vectors removed)")
            return {"status": "deleted", "file_path": norm_path, "vectors_removed": count}
        except Exception as e:
            logger.error(f"Delete error {file_path}: {e}")
            return {"status": "error", "reason": f"delete_error: {e}"}

    @staticmethod
    def _compute_hash(file_path: Path) -> str:
        """SHA-256 hash of a file."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(8192), b""):
                sha.update(block)
        return sha.hexdigest()

    def run_queue_worker(self):
        """Main loop that dequeues and processes jobs from Redis queue."""
        logger.info("Queue worker started, waiting for jobs...")

        while True:
            try:
                # Blocking pop
                job = self.redis.brpop(self._queue_name, timeout=self._brpop_timeout)
                if job is None:
                    continue

                _, raw = job
                task = json.loads(raw)
                file_path = task.get("file_path", "")
                retries = task.get("retries", 0)

                event = task.get("event", "modified")
                logger.info(f"Processing: {file_path} (event={event}, retry={retries})")

                if event == "deleted":
                    result = self.delete_file(file_path)
                else:
                    result = self.process_file(file_path)

                if result["status"] == "error" and retries < self._max_retries:
                    # Move to retry queue
                    task["retries"] = retries + 1
                    self.redis.lpush(self._retry_queue, json.dumps(task))
                    logger.warning(f"Retry {retries+1}/{self._max_retries}: {file_path}")
                elif result["status"] == "error":
                    # Dead letter
                    task["error"] = result.get("reason", "unknown")
                    self.redis.lpush(self._dead_letter_queue, json.dumps(task))
                    logger.error(f"Dead letter: {file_path}")

            except KeyboardInterrupt:
                logger.info("Worker shutting down...")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(1)


def batch_ingest(directory: str):
    """Index all files in a directory sequentially."""
    worker = IndexingWorker()
    dir_path = Path(directory)

    if not dir_path.exists():
        logger.error(f"Directory not found: {directory}")
        return

    files = [f for f in dir_path.rglob("*") if f.is_file() and f.suffix.lower() in worker._supported_extensions]
    logger.info(f"Found {len(files)} files to index in {directory}")

    success = 0
    errors = 0
    skipped = 0

    for i, file_path in enumerate(files, 1):
        logger.info(f"[{i}/{len(files)}] {file_path}")
        result = worker.process_file(str(file_path))

        if result["status"] == "success":
            success += 1
        elif result["status"] == "skipped":
            skipped += 1
        else:
            errors += 1

    logger.info(f"=== Batch complete: {success} indexed, {skipped} skipped, {errors} errors ===")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        # batch mode: python worker.py batch /path/to/docs
        docs_dir = sys.argv[2] if len(sys.argv) > 2 else "/documents"
        batch_ingest(docs_dir)
    else:
        # queue worker mode
        worker = IndexingWorker()
        worker.run_queue_worker()
