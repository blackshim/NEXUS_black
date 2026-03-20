"""
Conversation Log Manager

Saves and retrieves conversation logs in JSONL format.
Supports the NFD paper's 6-category classification system.

Categories:
- operational: General task processing records
- reasoning: AI reasoning process
- pattern: Repeated pattern observations
- error: Incorrect/corrected answers
- context: Environment/context information
- insight: Insight fragments

Usage:
    save_log("domains/my-domain/logs", {
        "user": "user_name",
        "category": "operational",
        "conversation": [...],
        "extracted": {...}
    })
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))

VALID_CATEGORIES = {"operational", "reasoning", "pattern", "error", "context", "insight"}


def save_log(log_dir: str, log_entry: dict) -> str:
    """Saves a conversation log to a JSONL file.

    Args:
        log_dir: Log directory path (e.g., "domains/my-domain/logs")
        log_entry: Log data (user, category, conversation, etc.)

    Returns:
        Saved log ID
    """
    now = datetime.now(KST)
    date_str = now.strftime("%Y-%m-%d")
    log_file = Path(log_dir) / f"{date_str}.jsonl"

    # Create directory
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Count today's logs (for ID generation)
    existing_count = 0
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            existing_count = sum(1 for _ in f)

    # Validate category
    category = log_entry.get("category", "operational")
    if category not in VALID_CATEGORIES:
        category = "operational"

    # Assemble log structure
    log = {
        "id": f"log-{date_str}-{existing_count + 1:03d}",
        "timestamp": now.isoformat(),
        "session_id": log_entry.get("session_id", ""),
        "user": log_entry.get("user", "unknown"),
        "category": category,
        "conversation": log_entry.get("conversation", []),
        "extracted": log_entry.get("extracted", {}),
        "crystallization_status": "pending",
        "knowledge_item_id": log_entry.get("knowledge_item_id", ""),
        "result": log_entry.get("result", "")
    }

    # Append to JSONL
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    return log["id"]


def load_logs(
    log_dir: str,
    date: str = None,
    category: str = None,
    limit: int = 100
) -> list[dict]:
    """Retrieves conversation logs.

    Args:
        log_dir: Log directory path
        date: Date filter (YYYY-MM-DD, None for all)
        category: Category filter
        limit: Maximum number of results

    Returns:
        List of logs (newest first)
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return []

    logs = []

    if date:
        files = [log_path / f"{date}.jsonl"]
    else:
        files = sorted(log_path.glob("*.jsonl"), reverse=True)

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

    # Sort by newest first
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs[:limit]


def get_log_stats(log_dir: str) -> dict:
    """Returns log statistics.

    Returns:
        {"total": N, "by_category": {...}, "by_date": {...}, "by_result": {...}}
    """
    logs = load_logs(log_dir, limit=10000)

    by_category = {}
    by_date = {}
    by_result = {}

    for log in logs:
        cat = log.get("category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1

        date = log.get("timestamp", "")[:10]
        by_date[date] = by_date.get(date, 0) + 1

        result = log.get("result", "")
        if result:
            by_result[result] = by_result.get(result, 0) + 1

    return {
        "total": len(logs),
        "by_category": by_category,
        "by_date": dict(sorted(by_date.items(), reverse=True)[:7]),
        "by_result": by_result
    }
