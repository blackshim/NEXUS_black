"""
skill.md Conversion Material Provider (Design Doc 4.1.4 Phase 3)

Provides materials for converting a refined process.md into skill.md.
The actual conversion is performed by the LLM (agent).

Provides SCAR principles and framework-specific process structure guides as references to the LLM,
which then freely writes skill.md tailored to the domain.
No fixed templates — the process section structure is determined by the framework.

Usage:
    prompt = build_skill_prompt("domains/my-domain", "my-domain", "My Domain", "diagnostic-branching")
    # -> Return to agent -> LLM writes skill.md -> save with save_skill
"""

import json
from pathlib import Path


# Reference file paths (same folder as this file)
_THIS_DIR = Path(__file__).resolve().parent
SCAR_GUIDE_PATH = _THIS_DIR / "scar_guide.md"
FRAMEWORKS_PATH = _THIS_DIR / "frameworks.md"

# Available Core MCP tool list
AVAILABLE_TOOLS = {
    "domain-search.search_knowledge": "Search the domain knowledge DB (JSON) by keyword",
    "domain-add.add_knowledge": "Add a new item to the domain knowledge DB",
    "domain-add.save_conversation_log": "Save conversation log",
    "domain-export.export_knowledge": "Export domain knowledge DB to Excel",
    "doc-search.search_documents": "Vector search in indexed documents (PDF, manuals, etc.)",
    "doc-summary.summarize_document": "Summarize a specific document in full",
    "doc-summary.summarize_topic": "Comprehensive search and summary by topic",
    "data-analysis.analyze_spreadsheet": "Analyze Excel/CSV file structure",
    "data-analysis.query_data": "Aggregate/filter Excel/CSV data",
    "indexing-admin.get_indexing_status": "Query indexing status",
}

# Metadata fields (excluded from knowledge extraction targets)
META_FIELDS = {
    "id", "source", "created_at", "created_by", "usage_stats",
    "category", "promoted_at"
}


def _read_file(path: Path) -> str:
    """Reads and returns file content. Returns empty string if file doesn't exist."""
    if path.exists():
        return path.read_text(encoding='utf-8')
    return ""


def _extract_knowledge_fields(domain_dir: str) -> list[str]:
    """Automatically identifies knowledge field list from domain_knowledge.json."""
    json_path = Path(domain_dir) / "domain_knowledge.json"
    if not json_path.exists():
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []

    all_keys = set()
    for item in data.get("items", [])[:10]:
        all_keys.update(item.keys())

    fields = [k for k in all_keys if k not in META_FIELDS]
    return sorted(fields) if fields else []


def build_skill_prompt(
    domain_dir: str,
    domain_name: str,
    display_name: str,
    framework_id: str,
) -> str:
    """Generates the skill.md conversion prompt.

    Combines scar_guide.md + frameworks.md + process.md + domain_knowledge.json fields +
    MCP tool list to return a prompt that enables the LLM to write skill.md.

    Args:
        domain_dir: Domain folder path
        domain_name: Domain name
        display_name: Display name
        framework_id: Selected framework ID
    """
    process_content = _read_file(Path(domain_dir) / "process.md")
    scar_guide = _read_file(SCAR_GUIDE_PATH)
    frameworks = _read_file(FRAMEWORKS_PATH)
    knowledge_fields = _extract_knowledge_fields(domain_dir)

    tools_list = "\n".join(f"- `{tool}` — {desc}" for tool, desc in AVAILABLE_TOOLS.items())
    fields_list = "\n".join(f"- {f}" for f in knowledge_fields) if knowledge_fields else "- (domain_knowledge.json has not been generated yet)"

    prompt = f"""You are a skill.md author.
Based on the materials below, write the skill.md for the {display_name} domain.

## Writing Principles (SCAR Guide)

{scar_guide}

## Framework Reference

Selected framework: **{framework_id}**
Find the "process structure guide" for this framework below and use it as reference.

{frameworks}

## Materials

### Refined process.md

{process_content}

### Available MCP Tools

{tools_list}

### Knowledge Extraction Fields (based on domain_knowledge.json)

{fields_list}

### Domain Information

- Domain name: {domain_name}
- Display name: {display_name}
- Framework: {framework_id}

## Writing Instructions

1. Follow the SCAR 4 principles from scar_guide.md.
2. Follow the skill.md universal skeleton (role, tools, process, knowledge extraction fields, result criteria, rules, on completion).
3. **The process section must follow the {framework_id} process structure guide.** This is not a fixed template.
4. Specify MCP tool calls deterministically (if this condition then always this tool).
5. Use MUST/SHOULD/MAY to indicate constraint levels.
6. Keep it under 500 lines, under 5000 words.
7. Include domain-add.save_conversation_log call instructions in the "On Completion" section.
"""
    return prompt


def save_skill(domain_dir: str, content: str) -> str:
    """Saves the skill.md written by the LLM to a file.

    Args:
        domain_dir: Domain folder path
        content: skill.md content

    Returns:
        Saved file path
    """
    output_path = Path(domain_dir) / "skill.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding='utf-8')
    return str(output_path)
