"""
NEXUS Core MCP: domain-search

Keyword-based search in domains/{domain_name}/domain_knowledge.json.
A universal search tool used by all domains.

Design spec:
- DOMAINS_BASE env var specifies the domains/ folder path
- All tools take domain_name parameter -> read domains/{domain_name}/domain_knowledge.json
- Multi-domain support: same MCP server can search multiple domains

Tools:
- search_knowledge(domain_name, keyword, category): Search JSON knowledge DB by keyword
- get_knowledge_stats(domain_name): View JSON knowledge DB statistics
"""

import json
import logging
import os
import sys
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
logger = logging.getLogger("nexus.mcp.domain-search")

mcp = FastMCP("nexus-domain-search")

DOMAINS_BASE = os.environ.get("DOMAINS_BASE", "")
if not DOMAINS_BASE:
    logger.warning("DOMAINS_BASE environment variable is not set.")
else:
    logger.info(f"Domains base: {DOMAINS_BASE}")


def _get_knowledge_path(domain_name: str) -> Path:
    """Return the path to domain_knowledge.json for the domain."""
    return Path(DOMAINS_BASE) / domain_name / "domain_knowledge.json"


def _load_knowledge(domain_name: str) -> dict:
    """Read and return JSON file."""
    path = _get_knowledge_path(domain_name)
    if not path.exists():
        return {"error": f"JSON file not found: {path}"}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search_knowledge(domain_name: str, keyword: str, category: str = "") -> str:
    """Keyword search in domain knowledge DB (JSON).
    Searches across all fields: error codes, symptoms, part names, actions, etc.

    Args:
        domain_name: Domain name (e.g., "my-domain")
        keyword: Search keyword (e.g., "detector communication error", "E2001", "conveyor")
        category: Category filter (optional, e.g., "detector", "generator")
    """
    if not DOMAINS_BASE:
        return "DOMAINS_BASE environment variable is not set."

    data = _load_knowledge(domain_name)
    if "error" in data and "items" not in data:
        return f"JSON load failed: {data['error']}"

    items = data.get("items", [])
    keyword_lower = keyword.strip().lower()
    keyword_empty = not keyword_lower

    keyword_words = [w for w in keyword_lower.split() if len(w) > 1] if not keyword_empty else []

    SKIP_FIELDS = {"id", "usage_stats", "created_at", "created_by", "source",
                   "verified_by", "verification_status", "conversation_ref"}

    results = []
    for item in items:
        if category:
            item_cat = str(item.get("category", "")).lower()
            if category.lower() not in item_cat:
                continue

        searchable_parts = []
        for key, value in item.items():
            if key in SKIP_FIELDS:
                continue
            if isinstance(value, str):
                searchable_parts.append(value.lower())
            elif isinstance(value, list):
                for v in value:
                    if isinstance(v, str):
                        searchable_parts.append(v.lower())
        searchable = " ".join(searchable_parts)

        if keyword_empty:
            results.append((item, 1))
        elif keyword_lower in searchable:
            results.append((item, 2))
        elif keyword_words and all(w in searchable for w in keyword_words):
            results.append((item, 1))

    def sort_key(item_score):
        item, score = item_score
        stats = item.get("usage_stats", {})
        return (-score, -stats.get("success_rate", 0), -stats.get("suggested", 0))
    results.sort(key=sort_key)
    results = [item for item, _ in results]

    if not results:
        return f"No knowledge found for '{keyword}'. (out of {len(items)} total items)"

    output = f"**'{keyword}' search results: {len(results)} items** (total {len(items)} items, domain: {domain_name})\n\n"
    for i, item in enumerate(results[:20], 1):
        output += f"### [{i}] {item.get('id', '?')}\n"
        for key, value in item.items():
            if key in ("id", "usage_stats", "source", "created_at", "created_by",
                        "verified_by", "verification_status", "conversation_ref"):
                continue
            if value and str(value).strip():
                output += f"- **{key}:** {value}\n"
        stats = item.get("usage_stats", {})
        if stats.get("suggested", 0) > 0:
            output += f"- **Usage stats:** suggested {stats['suggested']} times, resolved {stats.get('resolved',0)} times, success rate {stats.get('success_rate',0):.0%}\n"
        output += "\n"

    return output


@mcp.tool()
def get_knowledge_stats(domain_name: str) -> str:
    """Retrieves the current status of the domain knowledge DB.

    Args:
        domain_name: Domain name (e.g., "my-domain")
    """
    if not DOMAINS_BASE:
        return "DOMAINS_BASE environment variable is not set."

    data = _load_knowledge(domain_name)
    if "error" in data and "items" not in data:
        return f"JSON load failed: {data['error']}"

    meta = data.get("_meta", {})
    items = data.get("items", [])

    sources = {}
    categories = {}
    for item in items:
        src = item.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
        cat = item.get("category", "uncategorized")
        categories[cat] = categories.get(cat, 0) + 1

    output = f"## Domain Knowledge DB Status ({domain_name})\n\n"
    output += f"- **Total items:** {len(items)}\n"
    output += f"- **Domain:** {meta.get('domain', '?')}\n"
    output += f"- **Last updated:** {meta.get('last_crystallized', '?')}\n\n"

    output += "**By source:**\n"
    for src, cnt in sorted(sources.items()):
        output += f"- {src}: {cnt}\n"

    output += "\n**By category:**\n"
    for cat, cnt in sorted(categories.items(), key=lambda x: -x[1]):
        output += f"- {cat}: {cnt}\n"

    return output


if __name__ == "__main__":
    mcp.run(transport="stdio")
