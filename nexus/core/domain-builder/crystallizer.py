"""
Knowledge Crystallization Engine

Extracts knowledge from conversation logs and structures it into domain_knowledge.json.
Tracks usage_stats to automatically manage knowledge reliability.

Core Principles:
- LLM-based judgment (not hardcoded)
- Result criteria are defined by process.md
- Designed to operate without human oversight

Usage:
    # Update usage_stats
    update_usage_stats("domain_knowledge.json", "NSE-ERR-0011", "resolved")

    # Generate prompt for knowledge extraction from conversation
    prompt = build_extraction_prompt(conversation, knowledge_fields)
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))


def update_usage_stats(
    knowledge_json_path: str,
    item_id: str,
    result: str
) -> dict:
    """Updates the usage_stats of a knowledge item.

    Args:
        knowledge_json_path: Path to domain_knowledge.json
        item_id: Knowledge item ID
        result: "resolved" | "failed" | "ongoing" | "unrelated"

    Returns:
        {"status": "updated", "item_id": ..., "new_stats": {...}}
    """
    path = Path(knowledge_json_path)
    if not path.exists():
        return {"error": f"JSON file not found: {knowledge_json_path}"}

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data.get("items", [])
    target = None
    for item in items:
        if item.get("id") == item_id:
            target = item
            break

    if target is None:
        return {"error": f"Item not found: {item_id}"}

    stats = target.get("usage_stats", {
        "suggested": 0, "resolved": 0, "failed": 0, "success_rate": 0
    })

    stats["suggested"] = stats.get("suggested", 0) + 1

    if result == "resolved":
        stats["resolved"] = stats.get("resolved", 0) + 1
    elif result == "failed":
        stats["failed"] = stats.get("failed", 0) + 1
    # ongoing, unrelated only increment suggested

    # Recalculate success rate
    total_decisive = stats.get("resolved", 0) + stats.get("failed", 0)
    if total_decisive > 0:
        stats["success_rate"] = round(stats["resolved"] / total_decisive, 2)

    target["usage_stats"] = stats

    # Backup then save
    import shutil
    bak = str(path) + ".bak"
    try:
        shutil.copy2(path, bak)
    except Exception:
        pass

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "status": "updated",
        "item_id": item_id,
        "result": result,
        "new_stats": stats
    }


def build_extraction_prompt(
    conversation: list[dict],
    knowledge_fields: list[str]
) -> str:
    """Generates an LLM prompt for extracting knowledge from a conversation.

    This prompt, when passed to an LLM, returns structured knowledge items.
    Domain Builder uses this prompt for knowledge extraction.

    Args:
        conversation: Conversation content [{"role": "user"|"nexus", "text": "..."}]
        knowledge_fields: List of fields to extract (defined in process.md)

    Returns:
        Prompt string to pass to the LLM
    """
    conv_text = ""
    for msg in conversation:
        role = "User" if msg.get("role") == "user" else "NEXUS"
        conv_text += f"{role}: {msg.get('text', '')}\n"

    fields_desc = ", ".join(knowledge_fields)

    prompt = f"""Please extract knowledge items from the following conversation.

Fields to extract: {fields_desc}

Conversation content:
{conv_text}

Please extract from the above conversation in the following JSON format:
{{
{chr(10).join(f'  "{f}": "..."' for f in knowledge_fields)}
}}

If the information is not present in the conversation, leave it as an empty string.
"""
    return prompt


def build_result_classification_prompt(
    response_text: str,
    result_criteria: dict
) -> str:
    """Generates an LLM prompt for classifying whether a user response is success/failure.

    Args:
        response_text: User's response text
        result_criteria: Result criteria dict (defined in process.md)
            e.g., {"positive": "Problem resolved", "negative": "Not resolved", ...}

    Returns:
        Prompt string to pass to the LLM
    """
    criteria_text = ""
    for key, desc in result_criteria.items():
        criteria_text += f"- {key}: {desc}\n"

    prompt = f"""Please classify the user's response.

Classification criteria:
{criteria_text}

User response: "{response_text}"

Select only one of the above criteria and respond with the key value only:
"""
    return prompt


def check_promotion_candidates(
    knowledge_json_path: str,
    min_usage: int = 5,
    min_success_rate: float = 0.8
) -> list[dict]:
    """Finds knowledge items that meet promotion criteria.

    Args:
        knowledge_json_path: Path to domain_knowledge.json
        min_usage: Minimum usage count
        min_success_rate: Minimum success rate

    Returns:
        List of promotion candidate items
    """
    path = Path(knowledge_json_path)
    if not path.exists():
        return []

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    candidates = []
    for item in data.get("items", []):
        stats = item.get("usage_stats", {})
        suggested = stats.get("suggested", 0)
        success_rate = stats.get("success_rate", 0)

        if suggested >= min_usage and success_rate >= min_success_rate:
            # Only items from conversation are promotion candidates (excel_import is already reflected)
            if item.get("source") == "conversation":
                candidates.append(item)

    return candidates


def generate_weekly_report(
    knowledge_json_path: str,
    log_dir: str
) -> str:
    """Generates a weekly report.

    Returns:
        Weekly report in markdown format
    """
    from log_manager import get_log_stats

    # Knowledge DB status
    path = Path(knowledge_json_path)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get("items", [])
        meta = data.get("_meta", {})
    else:
        items = []
        meta = {}

    stats = meta.get("stats", {})
    total = len(items)
    from_excel = stats.get("from_excel", 0)
    from_conv = stats.get("from_conversation", 0)

    # Promotion candidates
    candidates = check_promotion_candidates(knowledge_json_path)

    # Log statistics
    log_stats = get_log_stats(log_dir)

    # Top/bottom success rates
    items_with_usage = [i for i in items if i.get("usage_stats", {}).get("suggested", 0) > 0]
    items_with_usage.sort(key=lambda x: x["usage_stats"]["success_rate"], reverse=True)

    now = datetime.now(KST)
    report = f"# NEXUS Weekly Report\n"
    report += f"> {now.strftime('%Y-%m-%d %H:%M')}\n\n"

    report += f"## Knowledge DB Status\n"
    report += f"- Total items: {total} (Excel: {from_excel}, Conversation: {from_conv})\n"
    report += f"- Domain: {meta.get('domain', '?')}\n\n"

    report += f"## This Week's Activity\n"
    report += f"- Conversation logs: {log_stats.get('total', 0)}\n"
    if log_stats.get("by_result"):
        for result, cnt in log_stats["by_result"].items():
            report += f"  - {result}: {cnt}\n"
    report += "\n"

    if candidates:
        report += f"## Promotion Candidates ({len(candidates)})\n"
        report += "The following items meet auto-promotion criteria:\n\n"
        for c in candidates:
            s = c["usage_stats"]
            report += f"- **{c['id']}**: {c.get('description', '')[:50]} "
            report += f"(used {s['suggested']} times, success rate {s['success_rate']:.0%})\n"
        report += "\n"
    else:
        report += "## Promotion Candidates\nNo items meet promotion criteria.\n\n"

    if items_with_usage:
        report += "## Top 3 by Success Rate\n"
        for item in items_with_usage[:3]:
            s = item["usage_stats"]
            report += f"- {item['id']}: {item.get('description', '')[:40]} — success rate {s['success_rate']:.0%} ({s['suggested']} times)\n"

        low = [i for i in items_with_usage if i["usage_stats"]["success_rate"] < 0.5]
        if low:
            report += "\n## Low Success Rate (below 50%) — Review Needed\n"
            for item in low[:3]:
                s = item["usage_stats"]
                report += f"- {item['id']}: {item.get('description', '')[:40]} — success rate {s['success_rate']:.0%} ({s['suggested']} times)\n"

    return report
