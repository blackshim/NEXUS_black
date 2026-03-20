"""
NEXUS indexing-admin MCP server -- indexing management.

Tools:
- index_file: Manually index a specific file
- index_folder: Index an entire folder
- get_indexing_status: View indexing status
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import httpx
import redis

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
logger = logging.getLogger("nexus.mcp.indexing-admin")

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "nexus-qdrant-change-me")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://localhost:8080")
WORKER_PATH = os.environ.get("WORKER_PATH",
    str(Path(__file__).parent.parent.parent / "indexing" / "worker.py"))
PYTHON = sys.executable

http = httpx.Client(timeout=10.0)
mcp = FastMCP("nexus-indexing-admin")


def _run_worker(args: list[str], timeout: int = 120) -> str:
    """Run Worker via subprocess (prevents event loop blocking)."""
    env = os.environ.copy()
    env.update({
        "QDRANT_URL": QDRANT_URL,
        "QDRANT_API_KEY": QDRANT_API_KEY,
        "EMBEDDING_URL": EMBEDDING_URL,
        "REDIS_URL": REDIS_URL,
        "PYTHONPATH": str(Path(WORKER_PATH).parent),
    })

    cmd = [PYTHON, WORKER_PATH] + args
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
        stdin=subprocess.DEVNULL, env=env, cwd=str(Path(WORKER_PATH).parent)
    )

    output = proc.stdout + proc.stderr
    return output


@mcp.tool()
def index_file(file_path: str) -> str:
    """Manually indexes a specific file.

    Args:
        file_path: Absolute path of the file to index
    """
    path = Path(file_path)
    if not path.exists():
        return f"File does not exist: {file_path}"

    # Run worker via subprocess (single file mode)
    import json as _json
    _args = _json.dumps({
        "worker_dir": str(Path(WORKER_PATH).parent),
        "file_path": file_path,
        "qdrant_url": QDRANT_URL,
        "qdrant_api_key": QDRANT_API_KEY,
        "embedding_url": EMBEDDING_URL,
        "redis_url": REDIS_URL,
    })
    script = '''
import sys, os, json
args = json.loads(sys.argv[1])
sys.path.insert(0, args["worker_dir"])
os.environ["QDRANT_URL"] = args["qdrant_url"]
os.environ["QDRANT_API_KEY"] = args["qdrant_api_key"]
os.environ["EMBEDDING_URL"] = args["embedding_url"]
os.environ["REDIS_URL"] = args["redis_url"]
from worker import IndexingWorker
w = IndexingWorker()
result = w.process_file(args["file_path"])
print(json.dumps(result, ensure_ascii=False))
'''
    proc = subprocess.run(
        [PYTHON, "-c", script, _args],
        capture_output=True, text=True, timeout=120,
        stdin=subprocess.DEVNULL
    )

    if proc.returncode != 0:
        error_msg = proc.stderr[:500] if proc.stderr else "unknown error"
        return f"Indexing failed: {error_msg}"

    try:
        result = json.loads(proc.stdout.strip().split("\n")[-1])
        status = result.get("status", "unknown")
        if status == "success":
            return (
                f"Indexing complete: {result.get('file_path', file_path)}\n"
                f"- Chunks: {result.get('chunks', 0)}\n"
                f"- Workspace: {result.get('workspace', 'general')}\n"
                f"- Confidential: {'Yes' if result.get('confidential') else 'No'}"
            )
        elif status == "skipped":
            return f"No changes (already indexed): {file_path}"
        else:
            return f"Indexing failed: {result.get('reason', 'unknown')}"
    except (json.JSONDecodeError, IndexError):
        return f"Indexing complete (detailed result parsing failed)\nOutput: {proc.stdout[:300]}"


@mcp.tool()
def index_folder(folder_path: str) -> str:
    """Indexes all documents in a folder.

    Args:
        folder_path: Absolute path of the folder to index
    """
    path = Path(folder_path)
    if not path.exists():
        return f"Folder does not exist: {folder_path}"

    supported = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".csv",
                 ".txt", ".md", ".log", ".json", ".xml", ".yaml", ".yml", ".html", ".htm"}
    files = [f for f in path.rglob("*") if f.is_file() and f.suffix.lower() in supported]

    if not files:
        return f"No files to index: {folder_path}"

    # Run batch mode via subprocess
    _args2 = _json.dumps({
        "worker_dir": str(Path(WORKER_PATH).parent),
        "folder_path": folder_path,
        "qdrant_url": QDRANT_URL,
        "qdrant_api_key": QDRANT_API_KEY,
        "embedding_url": EMBEDDING_URL,
        "redis_url": REDIS_URL,
    })
    script2 = '''
import sys, os, json
args = json.loads(sys.argv[1])
sys.path.insert(0, args["worker_dir"])
os.environ["QDRANT_URL"] = args["qdrant_url"]
os.environ["QDRANT_API_KEY"] = args["qdrant_api_key"]
os.environ["EMBEDDING_URL"] = args["embedding_url"]
os.environ["REDIS_URL"] = args["redis_url"]
from worker import batch_ingest
batch_ingest(args["folder_path"])
'''
    proc = subprocess.run(
        [PYTHON, "-c", script2, _args2],
        capture_output=True, text=True, timeout=600,
        stdin=subprocess.DEVNULL
    )

    # Parse result
    output = proc.stderr + proc.stdout
    lines = output.split("\n")

    # Find "Batch complete" line
    for line in lines:
        if "Batch complete" in line or "indexed" in line.lower():
            return f"Folder indexing complete: {folder_path}\n{line.strip()}\nFiles found: {len(files)}"

    return f"Folder indexing complete: {folder_path}\nFiles found: {len(files)}\n(See server stderr for detailed logs)"


@mcp.tool()
def get_indexing_status() -> str:
    """Retrieves current indexing status (Qdrant vector count, per-file statistics, queue status)."""
    output_parts = []

    # 1. Qdrant collection info
    try:
        resp = http.get(
            f"{QDRANT_URL}/collections/documents",
            headers={"api-key": QDRANT_API_KEY}
        )
        resp.raise_for_status()
        col_info = resp.json()["result"]
        total_vectors = col_info.get("points_count", 0)
        output_parts.append(f"## Qdrant Status\n- Total vectors: {total_vectors:,}")
    except Exception as e:
        output_parts.append(f"## Qdrant Status\n- Query failed: {e}")

    # 2. Per-file type statistics
    try:
        resp = http.post(
            f"{QDRANT_URL}/collections/documents/points/scroll",
            headers={"api-key": QDRANT_API_KEY, "Content-Type": "application/json"},
            json={"limit": 10000, "with_payload": ["file_path", "file_type", "workspace", "confidential"]}
        )
        resp.raise_for_status()
        points = resp.json()["result"]["points"]

        # Per-file statistics
        files: dict[str, dict] = {}
        for pt in points:
            fp = pt["payload"].get("file_path", "unknown")
            fname = fp.replace("\\", "/").split("/")[-1]
            if fname not in files:
                files[fname] = {
                    "type": pt["payload"].get("file_type", "?"),
                    "workspace": pt["payload"].get("workspace", "?"),
                    "chunks": 0,
                    "confidential": pt["payload"].get("confidential", False),
                }
            files[fname]["chunks"] += 1

        output_parts.append(f"\n## Indexed Files ({len(files)})")
        output_parts.append("| File | Type | Chunks | Workspace | Confidential |")
        output_parts.append("|------|------|--------|-----------|--------------|")
        for fname, info in sorted(files.items()):
            conf = "Yes" if info["confidential"] else "-"
            output_parts.append(f"| {fname} | {info['type']} | {info['chunks']} | {info['workspace']} | {conf} |")

        # Per-type totals
        type_counts: dict[str, int] = {}
        for info in files.values():
            t = info["type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        type_str = ", ".join(f"{t}: {c}" for t, c in sorted(type_counts.items()))
        output_parts.append(f"\nBy file type: {type_str}")

    except Exception as e:
        output_parts.append(f"\n## File Statistics\n- Query failed: {e}")

    # 3. Redis queue status
    try:
        r = redis.from_url(REDIS_URL)
        queue_len = r.llen("nexus:indexing:queue")
        retry_len = r.llen("nexus:indexing:retry")
        dead_len = r.llen("nexus:indexing:dead_letter")
        output_parts.append(f"\n## Queue Status\n- Pending: {queue_len} | Retry: {retry_len} | Failed: {dead_len}")

        if dead_len > 0:
            # Show dead letter contents (max 5)
            dead_items = r.lrange("nexus:indexing:dead_letter", 0, 4)
            output_parts.append("\n### Failed Items:")
            for item in dead_items:
                try:
                    task = json.loads(item)
                    output_parts.append(f"- {task.get('file_path', '?')}: {task.get('error', '?')}")
                except json.JSONDecodeError:
                    output_parts.append(f"- (parse failed)")
    except Exception as e:
        output_parts.append(f"\n## Queue Status\n- Redis connection failed: {e}")

    # 4. Embedding server status
    try:
        resp = http.get(f"{EMBEDDING_URL}/health")
        resp.raise_for_status()
        health = resp.json()
        embed_ok = "OK" if health.get("embedding_loaded") else "Not loaded"
        rerank_ok = "OK" if health.get("reranker_loaded") else "Not loaded"
        output_parts.append(f"\n## Embedding Server\n- Embedding model: {embed_ok} | Reranker: {rerank_ok}")
    except Exception as e:
        output_parts.append(f"\n## Embedding Server\n- Connection failed: {e}")

    return "\n".join(output_parts)


if __name__ == "__main__":
    mcp.run(transport="stdio")
