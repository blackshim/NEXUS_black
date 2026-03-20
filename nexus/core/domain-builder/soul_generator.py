"""
soul.md Generator (Design Doc Phase 4)

Input:
  - process.md (role, rules sections)
  - soul_answers.json (interactive question answers)

Output:
  # {agent name} — {role}
  ## Identity
  ## Core Rules
  ## Tool Usage Rules
  ## Response Style

Usage:
    questions = generate_soul_questions()
    # Agent collects user answers -> saves to soul_answers.json
    soul_md = generate_soul_md(answers, domain_name, display_name, process_md_path)
"""

import re
from pathlib import Path


def generate_soul_questions() -> list[dict]:
    """Returns the list of questions for soul.md generation."""
    return [
        # Identity
        {
            "phase": "Identity",
            "key": "agent_name",
            "question": "What should this AI be called? (default: NEXUS)",
            "default": "NEXUS"
        },
        {
            "phase": "Identity",
            "key": "role_description",
            "question": "Describe what this AI does in one sentence.",
            "default": "An AI assistant that connects and discovers organizational knowledge"
        },
        {
            "phase": "Identity",
            "key": "tone",
            "question": "What tone should it use? (formal/casual/neutral)",
            "default": "formal"
        },
        {
            "phase": "Identity",
            "key": "target_user",
            "question": "Does it respond directly to customers, or assist internal team members?",
            "default": "Assists internal team members"
        },
        # Rules
        {
            "phase": "Rules",
            "key": "must_not",
            "question": "Is there anything it must never do?",
            "default": "Never answer based on speculation"
        },
        {
            "phase": "Rules",
            "key": "safety_warning",
            "question": "Are there areas that require safety warnings?",
            "default": ""
        },
        {
            "phase": "Rules",
            "key": "unknown_handling",
            "question": "How should it handle questions it cannot answer?",
            "default": "State that no confirmed information is available and direct to the relevant department"
        },
        # Tool Rules
        {
            "phase": "Tool Rules",
            "key": "source_conflict",
            "question": "When multiple sources conflict, which takes priority?",
            "default": "Official manuals take priority, domain knowledge DB as supplementary"
        },
        {
            "phase": "Tool Rules",
            "key": "no_result_action",
            "question": "What should it do when no search results are found?",
            "default": "State that the information could not be found"
        },
    ]


def _parse_process_section(process_text: str, section_name: str) -> str:
    """Extracts content of a specific section (## Role, ## Rules, etc.) from process.md."""
    pattern = rf"^##\s*{re.escape(section_name)}\s*\n(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, process_text, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def generate_soul_md(
    answers: dict,
    domain_name: str,
    display_name: str,
    process_md_path: str = ""
) -> str:
    """Generates soul.md based on Design Doc Phase 4.

    Args:
        answers: Answers dict in {key: value} format
        domain_name: Domain name
        display_name: Display name
        process_md_path: process.md file path (for role/rules extraction)
    """
    # === Extract answers ===
    agent_name = answers.get("agent_name", "NEXUS")
    role_desc = answers.get("role_description", "An AI assistant that connects and discovers organizational knowledge")
    tone = answers.get("tone", "formal")
    target = answers.get("target_user", "Assists internal team members")
    must_not = answers.get("must_not", "")
    safety = answers.get("safety_warning", "")
    unknown = answers.get("unknown_handling", "")
    conflict = answers.get("source_conflict", "")
    no_result = answers.get("no_result_action", "")

    # === Extract role/rules from process.md ===
    process_role = ""
    process_rules = ""
    if process_md_path and Path(process_md_path).exists():
        process_text = Path(process_md_path).read_text(encoding="utf-8")
        process_role = _parse_process_section(process_text, "Role")
        if not process_role:
            # Fallback: parse Korean section header "역할" (= "Role")
            process_role = _parse_process_section(process_text, "역할")
        process_rules = _parse_process_section(process_text, "Rules")
        if not process_rules:
            # Fallback: parse Korean section header "규칙" (= "Rules")
            process_rules = _parse_process_section(process_text, "규칙")

    # === 1. Identity ===
    md = f"# {agent_name} — {role_desc}\n\n"
    md += "## Identity\n"
    md += f"I am {agent_name}, {role_desc}.\n"
    md += f"Current domain: {display_name}\n"
    md += f"Target users: {target}\n"
    if process_role:
        md += f"\n{process_role}\n"
    md += "\n"

    # === 2. Core Rules ===
    md += "## Core Rules\n"
    md += "- Cite sources in all answers. Format: [filename, page/sheet] or [domain knowledge DB, item ID]\n"
    md += '- If no source is available, state "Could not find relevant information in internal documents."\n'
    md += '- When the user requests "save this", "add this", or "store this", call domain-add.\n'
    if must_not:
        md += f"- {must_not}\n"
    if safety:
        md += f"- Safety warning: {safety}\n"
    if unknown:
        md += f"- Unknown questions: {unknown}\n"
    if process_rules:
        md += f"\n### Domain Rules (based on process.md)\n{process_rules}\n"
    md += "\n"

    # === 3. Tool Usage Rules ===
    md += "## Tool Usage Rules\n"
    md += "**Never search in memory folders or workspace files. Always use MCP tools.**\n\n"

    md += "### Domain Knowledge Search (domain-search)\n"
    md += f'- Keyword search: domain-search.search_knowledge (domain_name="{domain_name}", keyword="keyword")\n'
    md += f'- Status query: domain-search.get_knowledge_stats (domain_name="{domain_name}")\n\n'

    md += "### Document Search (doc-search)\n"
    md += '- Search: doc-search.search_documents (query="search term")\n\n'

    md += "### Knowledge Addition (domain-add)\n"
    md += f'- Add: domain-add.add_knowledge (domain_name="{domain_name}", description="description", cause="cause", solution="action")\n\n'

    md += "### Conversation Log Saving (domain-add)\n"
    md += f'- Save: domain-add.save_conversation_log (domain_name="{domain_name}", user="username", category="category", conversation_json="[conversation]", result="result")\n\n'

    md += "### Knowledge Export (domain-export)\n"
    md += f'- Export: domain-export.export_knowledge (domain_name="{domain_name}")\n\n'

    md += "### Document Summary (doc-summary)\n"
    md += '- Summary: doc-summary.summarize_document (file_path="filename")\n'
    md += '- By topic: doc-summary.summarize_topic (topic="topic")\n\n'

    md += "### Data Analysis (data-analysis)\n"
    md += '- Analysis: data-analysis.analyze_spreadsheet (file_name="filename")\n\n'

    md += "### Indexing Admin (indexing-admin)\n"
    md += "- Status: indexing-admin.get_indexing_status\n\n"

    if conflict:
        md += f"### On Source Conflict\n- {conflict}\n\n"
    if no_result:
        md += f"### On No Search Results\n- {no_result}\n\n"

    # === 4. Response Style ===
    md += "## Response Style\n"
    md += "- Respond in Korean.\n"
    if tone == "formal":
        md += "- Use formal speech style.\n"
    elif tone == "casual":
        md += "- Use casual speech style.\n"
    else:
        md += f"- {tone}\n"
    md += '- Concise but accurate. For uncertain content, state "this is estimated to be ~".\n'
    md += "- Always include sources from search results.\n"

    return md


def save_soul_md(content: str, output_path: str, sync_to_runtime: bool = False) -> str:
    """Saves soul.md to a file.

    Args:
        content: soul.md content
        output_path: Save path (domains/{domain}/soul.md)
        sync_to_runtime: If True, also copies to ~/.openclaw/workspace/SOUL.md.
            Default False — prevents workspace overwrite (builder workflow).
            Domain switching is performed explicitly via the switch_domain tool.
    """
    import shutil

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(content, encoding='utf-8')

    if sync_to_runtime:
        runtime_paths = [
            Path.home() / ".openclaw" / "workspace" / "SOUL.md",
            Path.home() / ".openclaw" / "agents" / "main" / "workspace" / "SOUL.md",
        ]
        for rp in runtime_paths:
            try:
                rp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(output_path, rp)
            except Exception:
                pass

    return output_path
