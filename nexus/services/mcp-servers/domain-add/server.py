"""
NEXUS Core MCP: domain-add

Adds new knowledge items to domains/{domain_name}/domain_knowledge.json.
A general-purpose tool called when "save this" is requested during conversation.

Design spec:
- DOMAINS_BASE env var specifies the domains/ folder path
- domain_name parameter specifies the target domain
- Duplicate check (description-based)
- Safe write (temp file + rename + backup)

Tools:
- add_knowledge(domain_name, description, ...): Add new item to JSON
"""

import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

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
logger = logging.getLogger("nexus.mcp.domain-add")

mcp = FastMCP("nexus-domain-add")
PYTHON = sys.executable

DOMAINS_BASE = os.environ.get("DOMAINS_BASE", "")
if not DOMAINS_BASE:
    logger.warning("DOMAINS_BASE environment variable is not set.")
else:
    logger.info(f"Domains base: {DOMAINS_BASE}")

KST = timezone(timedelta(hours=9))


def _get_knowledge_path(domain_name: str) -> Path:
    """Return the path to domain_knowledge.json for the domain."""
    return Path(DOMAINS_BASE) / domain_name / "domain_knowledge.json"


_ADD_ITEM_SCRIPT = '''
import json, sys, shutil, tempfile, os

args = json.loads(sys.argv[1])
json_path = args["json_path"]
new_item = args["new_item"]

# Read existing data
try:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    data = {"_meta": {"domain": "unknown", "schema_version": 1}, "items": []}

items = data.get("items", [])

# Duplicate check -- exact match based on description
def normalize(text):
    return text.lower().strip().replace("\\n", " ").replace("  ", " ") if text else ""

new_desc = normalize(new_item.get("description", ""))

for existing in items:
    ex_desc = normalize(existing.get("description", ""))
    if new_desc and new_desc == ex_desc:
        result = {"status": "duplicate", "existing_id": existing.get("id", "?"),
                  "message": f"Similar item already exists: {existing.get('id')}"}
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.exit(0)

# Add new item
items.append(new_item)
data["items"] = items

# Update metadata
meta = data.get("_meta", {})
stats = meta.get("stats", {})
stats["total_items"] = len(items)
source = new_item.get("source", "unknown")
stats[f"from_{source}"] = stats.get(f"from_{source}", 0) + 1
meta["stats"] = stats
meta["last_crystallized"] = new_item.get("created_at", "")
data["_meta"] = meta

# Backup
bak_path = json_path + ".bak"
try:
    shutil.copy2(json_path, bak_path)
except Exception:
    pass

# Safe write (temp file -> rename)
tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=os.path.dirname(json_path))
try:
    with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if os.path.exists(json_path):
        os.replace(tmp_path, json_path)
    else:
        os.rename(tmp_path, json_path)
except Exception as e:
    try:
        os.unlink(tmp_path)
    except Exception:
        pass
    result = {"status": "error", "message": f"Save failed: {str(e)}"}
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.exit(0)

result = {"status": "added", "id": new_item.get("id", "?"),
          "total_items": len(items)}
json.dump(result, sys.stdout, ensure_ascii=False)
'''


@mcp.tool()
def add_knowledge(
    domain_name: str,
    description: str,
    cause: str = "",
    solution: str = "",
    category: str = "",
    error_code: str = "",
    model: str = "",
    result: str = "",
    created_by: str = "",
    tags: str = ""
) -> str:
    """Adds a new item to the domain knowledge DB (JSON).
    Use this to save verified cases during conversation.

    Args:
        domain_name: Domain name (e.g., "my-domain")
        description: Symptom/situation description (required)
        cause: Cause
        solution: Action/resolution method
        category: Category (e.g., "detector", "generator")
        error_code: Error code (e.g., "E2001")
        model: Equipment model (e.g., "XIS-3500")
        result: Processing result (e.g., "resolved", "unresolved")
        created_by: Author
        tags: Tags (comma-separated)
    """
    if not DOMAINS_BASE:
        return "DOMAINS_BASE environment variable is not set."

    if not description.strip():
        return "description (symptom/situation description) is required."

    knowledge_path = _get_knowledge_path(domain_name)
    if not knowledge_path.exists():
        return f"Domain knowledge DB not found: {knowledge_path}"

    now = datetime.now(KST)
    short_id = uuid.uuid4().hex[:8]

    new_item = {
        "id": f"K-{now.strftime('%Y%m%d')}-{short_id}",
        "source": "conversation",
        "created_at": now.isoformat(),
        "created_by": created_by or "unknown",
        "description": description.strip(),
        "usage_stats": {
            "suggested": 0,
            "resolved": 0,
            "failed": 0,
            "success_rate": 0
        }
    }

    if cause: new_item["cause"] = cause.strip()
    if solution: new_item["solution"] = solution.strip()
    if category: new_item["category"] = category.strip()
    if error_code: new_item["error_code"] = error_code.strip()
    if model: new_item["model"] = model.strip()
    if result: new_item["result"] = result.strip()
    if tags: new_item["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    args = json.dumps({
        "json_path": str(knowledge_path),
        "new_item": new_item
    })

    proc = subprocess.run(
        [PYTHON, "-c", _ADD_ITEM_SCRIPT, args],
        capture_output=True, text=True, timeout=30,
        stdin=subprocess.DEVNULL
    )

    if proc.returncode != 0:
        return f"Save failed: {proc.stderr.strip()[:200]}"

    resp = json.loads(proc.stdout)

    if resp.get("status") == "duplicate":
        return f"A similar item already exists: {resp.get('existing_id')}. No new item was added."

    return (
        f"Knowledge item added.\n"
        f"- Domain: {domain_name}\n"
        f"- ID: {resp.get('id')}\n"
        f"- Total items: {resp.get('total_items')}\n"
        f"- Description: {description[:50]}..."
    )


# ===============================================
# Conversation log save/query (design spec 4.2.1)
# ===============================================

@mcp.tool()
def save_conversation_log(
    domain_name: str,
    user: str,
    category: str,
    conversation_json: str,
    extracted_json: str = "",
    session_id: str = "",
    knowledge_item_id: str = "",
    result: str = ""
) -> str:
    """Saves conversation log as JSONL in domains/{domain}/logs/.
    Automatically called after CS case completion.

    Args:
        domain_name: Domain name (e.g., "my-domain")
        user: User name
        category: Log classification (operational/reasoning/pattern/error/context/insight)
        conversation_json: Conversation content JSON (e.g., [{"role":"user","text":"..."},{"role":"nexus","text":"..."}])
        extracted_json: Extracted knowledge JSON (optional)
        session_id: Session ID (optional)
        knowledge_item_id: Related knowledge item ID (optional)
        result: Result (resolved/failed/ongoing/unrelated)
    """
    if not DOMAINS_BASE:
        return "DOMAINS_BASE environment variable is not set."

    log_dir = str(Path(DOMAINS_BASE) / domain_name / "logs")

    try:
        conversation = json.loads(conversation_json) if conversation_json else []
    except json.JSONDecodeError:
        return "Failed to parse conversation_json. Must be a JSON array format."

    try:
        extracted = json.loads(extracted_json) if extracted_json else {}
    except json.JSONDecodeError:
        extracted = {}

    valid_categories = {"operational", "reasoning", "pattern", "error", "context", "insight"}
    if category not in valid_categories:
        category = "operational"

    log_entry = {
        "user": user,
        "category": category,
        "conversation": conversation,
        "extracted": extracted,
        "session_id": session_id,
        "knowledge_item_id": knowledge_item_id,
        "result": result
    }

    # log_manager direct implementation (subprocess unnecessary -- simple file append)
    now = datetime.now(KST)
    date_str = now.strftime("%Y-%m-%d")
    log_file = Path(log_dir) / f"{date_str}.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    existing_count = 0
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            existing_count = sum(1 for _ in f)

    log = {
        "id": f"log-{date_str}-{existing_count + 1:03d}",
        "timestamp": now.isoformat(),
        "session_id": session_id,
        "user": user,
        "category": category,
        "conversation": conversation,
        "extracted": extracted,
        "crystallization_status": "pending",
        "knowledge_item_id": knowledge_item_id,
        "result": result
    }

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    return (
        f"Conversation log saved.\n"
        f"- ID: {log['id']}\n"
        f"- Domain: {domain_name}\n"
        f"- Category: {category}\n"
        f"- User: {user}"
    )


@mcp.tool()
def get_conversation_logs(
    domain_name: str,
    date: str = "",
    category: str = "",
    limit: int = 20
) -> str:
    """Retrieves conversation logs for a domain.

    Args:
        domain_name: Domain name (e.g., "my-domain")
        date: Date filter (YYYY-MM-DD, all if unspecified)
        category: Category filter (optional)
        limit: Maximum number of results (default 20)
    """
    if not DOMAINS_BASE:
        return "DOMAINS_BASE environment variable is not set."

    log_dir = Path(DOMAINS_BASE) / domain_name / "logs"
    if not log_dir.exists():
        return f"No logs found: {log_dir}"

    logs = []
    if date:
        files = [log_dir / f"{date}.jsonl"]
    else:
        files = sorted(log_dir.glob("*.jsonl"), reverse=True)

    for log_file in files:
        if not log_file.exists():
            continue
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if category and entry.get("category") != category:
                        continue
                    logs.append(entry)
                except json.JSONDecodeError:
                    continue
        if len(logs) >= limit:
            break

    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    logs = logs[:limit]

    if not logs:
        return "No logs found matching the criteria."

    result = f"## Conversation Logs ({len(logs)} entries)\n\n"
    for log in logs:
        result += f"**{log.get('id')}** | {log.get('timestamp', '')[:16]} | {log.get('category')} | {log.get('user')}\n"
        conv = log.get("conversation", [])
        if conv:
            first_msg = conv[0].get("text", "")[:60]
            result += f"  First message: {first_msg}...\n"
        result += "\n"

    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
