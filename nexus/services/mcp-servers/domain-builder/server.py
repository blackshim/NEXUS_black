"""
NEXUS Core MCP: domain-builder

MCP server for running Domain Builder interactively from the OpenClaw agent.
Wraps core/domain-builder/ modules as MCP tools.

All tools receive domain_name and operate in/out of domains/{domain_name}/ folder.

Input files (user must place in domains/{name}/):
  - process.md              (fixed name)
  - domain_knowledge.xlsx   (fixed name)

Output files (Domain Builder generates in the same folder):
  - process.md (refined)
  - domain_knowledge.json
  - skill.md
  - soul.md
  - config.yaml

Execution flow (design spec 4.1.4):
  "Build domain skill for {domain}"
  -> Phase 1: analyze_process -> conversational consulting -> save_refined_process
  -> Phase 2: analyze_excel -> convert_excel
  -> Phase 3: prepare_skill_materials -> LLM writes -> save_skill
  -> Phase 4: get_soul_questions -> generate_soul
  -> Phase 5: generate_domain_config
  -> Phase 6: trigger_indexing -> save_build_log

MCP tools (11):
  analyze_process, save_refined_process,
  analyze_excel, convert_excel,
  prepare_skill_materials, save_skill,
  get_soul_questions, generate_soul,
  generate_domain_config, trigger_indexing, save_build_log

Configuration:
  - DOMAINS_BASE: domains/ folder path (env var)
  - BUILDER_PATH: core/domain-builder/ module path (env var or auto-detected)
"""

import json
import logging
import os
import subprocess
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
logger = logging.getLogger("nexus.mcp.domain-builder")

mcp = FastMCP("nexus-domain-builder")
PYTHON = sys.executable

DOMAINS_BASE = os.environ.get("DOMAINS_BASE", "")

# core/domain-builder module path
BUILDER_PATH = os.environ.get("BUILDER_PATH", "")
if not BUILDER_PATH:
    _this = Path(__file__).resolve()
    BUILDER_PATH = str(_this.parent.parent.parent.parent / "core" / "domain-builder")

logger.info(f"Domain Builder module: {BUILDER_PATH}")
logger.info(f"Domains base: {DOMAINS_BASE}")


def _domain_dir(domain_name: str) -> Path:
    """Return the domain folder path."""
    if not DOMAINS_BASE:
        raise ValueError("DOMAINS_BASE environment variable is not set.")
    return Path(DOMAINS_BASE) / domain_name


def _run_builder_module(script: str) -> str:
    """Run core/domain-builder module via subprocess."""
    proc = subprocess.run(
        [PYTHON, "-c", script],
        capture_output=True, text=True, timeout=120,
        stdin=subprocess.DEVNULL
    )
    if proc.returncode != 0:
        return json.dumps({"error": proc.stderr.strip()[:500]}, ensure_ascii=False)
    return proc.stdout


# ===============================================
# Phase 1: process.md refinement
# ===============================================

@mcp.tool()
def analyze_process(domain_name: str) -> str:
    """Analyzes domains/{domain}/process.md and returns a framework selection prompt.
    This is the starting point of Domain Builder.

    The return value contains:
    1. frameworks.md (7 framework detailed reference)
    2. scar_guide.md (skill.md writing principles -- for completion judgment reference)
    3. process.md original text
    4. Instructions for LLM: framework selection + reasoning + conversational consulting guide

    The agent should then:
    - Select a framework and report to the user with reasoning
    - Ask about display_name
    - After approval, refine process.md through conversational consulting
    - Call save_refined_process after refinement is complete

    Args:
        domain_name: Domain name (e.g., "my-domain")
    """
    domain_dir = _domain_dir(domain_name)
    process_path = str(domain_dir / "process.md")

    if not Path(process_path).exists():
        return (f"Cannot find process.md: {process_path}\n"
                f"Please place process.md in the domains/{domain_name}/ folder.")

    try:
        sys.path.insert(0, BUILDER_PATH)
        from process_refiner import build_framework_selection_prompt

        prompt = build_framework_selection_prompt(str(domain_dir))
        return prompt
    except Exception as e:
        return f"Analysis failed: {str(e)[:300]}"


@mcp.tool()
def save_refined_process(domain_name: str, content: str) -> str:
    """Saves the refined process.md.
    Call this tool after Phase 1 conversational consulting is complete to save the refined content.

    Args:
        domain_name: Domain name
        content: Full content of refined process.md
    """
    domain_dir = _domain_dir(domain_name)

    try:
        sys.path.insert(0, BUILDER_PATH)
        from process_refiner import save_refined_process as _save

        path = _save(str(domain_dir), content)
        return f"process.md saved!\n- Path: {path}\n- Size: {len(content)} chars"
    except Exception as e:
        return f"Save failed: {str(e)[:300]}"


# ===============================================
# Phase 2: Excel analysis + JSON conversion
# ===============================================

@mcp.tool()
def analyze_excel(domain_name: str) -> str:
    """Analyzes the structure of domains/{domain}/domain_knowledge.xlsx.

    Args:
        domain_name: Domain name (e.g., "my-domain")
    """
    domain_dir = _domain_dir(domain_name)
    excel_path = str(domain_dir / "domain_knowledge.xlsx")

    if not Path(excel_path).exists():
        return (f"Cannot find domain_knowledge.xlsx: {excel_path}\n"
                f"Please place domain_knowledge.xlsx in the domains/{domain_name}/ folder.")

    script = f'''
import sys, json
sys.path.insert(0, {json.dumps(BUILDER_PATH)})
from analyzer import analyze_excel, format_analysis_report

analysis = analyze_excel({json.dumps(excel_path)})
report = format_analysis_report(analysis)
print(json.dumps({{"report": report}}, ensure_ascii=False))
'''
    output = _run_builder_module(script)
    try:
        result = json.loads(output)
        if "error" in result:
            return f"Analysis failed: {result['error']}"
        return result["report"]
    except Exception:
        return output


@mcp.tool()
def convert_excel(domain_name: str, skip_sheets: str = "") -> str:
    """Converts domains/{domain}/domain_knowledge.xlsx to JSON.
    Run after verifying the structure with analyze_excel.

    Args:
        domain_name: Domain name (e.g., "my-domain")
        skip_sheets: Sheets to skip (comma-separated, e.g., "Statistics,Sheet1")
    """
    domain_dir = _domain_dir(domain_name)
    excel_path = str(domain_dir / "domain_knowledge.xlsx")
    output_path = str(domain_dir / "domain_knowledge.json")

    if not Path(excel_path).exists():
        return f"Cannot find domain_knowledge.xlsx: {excel_path}"

    skip_list = [s.strip() for s in skip_sheets.split(",") if s.strip()] if skip_sheets else []

    script = f'''
import sys, json
sys.path.insert(0, {json.dumps(BUILDER_PATH)})
from converter import convert_excel_to_json

result = convert_excel_to_json(
    {json.dumps(excel_path)},
    {json.dumps(output_path)},
    {json.dumps(domain_name)},
    {json.dumps(skip_list)}
)
print(json.dumps(result, ensure_ascii=False))
'''
    output = _run_builder_module(script)
    try:
        result = json.loads(output)
        if result.get("status") == "ok":
            return f"JSON conversion complete!\n- Items: {result['total_items']}\n- Output: {result['output_path']}"
        return f"Conversion failed: {result.get('error', '?')}"
    except Exception:
        return output


# ===============================================
# Phase 3: skill.md generation (SCAR principles + framework guide)
# ===============================================

@mcp.tool()
def prepare_skill_materials(domain_name: str, display_name: str, framework_id: str) -> str:
    """Returns materials and prompt needed for skill.md conversion.
    This tool does not directly generate skill.md.
    Based on the returned prompt, the agent (LLM) writes skill.md,
    then saves it using the save_skill tool.

    Args:
        domain_name: Domain name (e.g., "my-domain")
        display_name: Display name (e.g., "NSE X-Ray Inspection Equipment CS")
        framework_id: Framework ID selected in Phase 1 (e.g., "diagnostic-branching")
    """
    domain_dir = _domain_dir(domain_name)

    try:
        sys.path.insert(0, BUILDER_PATH)
        from skill_generator import build_skill_prompt

        prompt = build_skill_prompt(str(domain_dir), domain_name, display_name, framework_id)
        return prompt
    except Exception as e:
        return f"Material generation failed: {str(e)[:300]}"


@mcp.tool()
def save_skill(domain_name: str, content: str) -> str:
    """Saves the LLM-written skill.md.
    Write skill.md based on prepare_skill_materials prompt, then save using this tool.

    Args:
        domain_name: Domain name
        content: Full content of skill.md
    """
    domain_dir = _domain_dir(domain_name)

    try:
        sys.path.insert(0, BUILDER_PATH)
        from skill_generator import save_skill as _save

        path = _save(str(domain_dir), content)
        return f"skill.md saved!\n- Path: {path}\n- Size: {len(content)} chars"
    except Exception as e:
        return f"Save failed: {str(e)[:300]}"


# ===============================================
# Phase 4: soul.md generation
# ===============================================

@mcp.tool()
def get_soul_questions(domain_name: str) -> str:
    """Returns the question list for soul.md generation.
    Ask the user these questions, collect answers,
    and save them as key:value pairs in domains/{domain}/soul_answers.json.
    After saving, call generate_soul.

    Args:
        domain_name: Domain name
    """
    try:
        sys.path.insert(0, BUILDER_PATH)
        from soul_generator import generate_soul_questions

        questions = generate_soul_questions()
        answers_path = str(Path(DOMAINS_BASE) / domain_name / "soul_answers.json")

        output = "## Questions for soul.md Generation\n\n"
        for i, q in enumerate(questions, 1):
            output += f"**Q{i}. [{q['phase']}] {q['question']}**\n"
            output += f"  Default: {q['default']}\n"
            output += f"  Key: {q['key']}\n\n"
        output += f"\n**Important:** After collecting answers, save them as JSON to the following file:\n"
        output += f"`{answers_path}`\n"
        output += 'Format: {"agent_name": "answer1", "role_description": "answer2", ...}\n'
        output += "After saving, call the generate_soul tool.\n"
        return output
    except Exception as e:
        return f"Question generation failed: {str(e)[:300]}"


@mcp.tool()
def generate_soul(domain_name: str, display_name: str) -> str:
    """Reads domains/{domain}/soul_answers.json and generates soul.md.
    The soul_answers.json file must be saved beforehand.

    Args:
        domain_name: Domain name
        display_name: Display name
    """
    domain_dir = _domain_dir(domain_name)
    answers_path = domain_dir / "soul_answers.json"
    output_path = str(domain_dir / "soul.md")

    if not answers_path.exists():
        return (f"Cannot find soul_answers.json: {answers_path}\n"
                f"Check questions with get_soul_questions, then save answers as JSON to the above path.")

    try:
        with open(answers_path, "r", encoding="utf-8") as f:
            answers = json.load(f)
    except Exception as e:
        return f"Failed to parse soul_answers.json: {str(e)[:200]}"

    try:
        sys.path.insert(0, BUILDER_PATH)
        from soul_generator import generate_soul_md, save_soul_md

        process_md_path = str(domain_dir / "process.md")
        content = generate_soul_md(answers, domain_name, display_name, process_md_path)
        save_soul_md(content, output_path)

        return f"soul.md generated!\n- Path: {output_path}\n- Size: {len(content)} chars"
    except Exception as e:
        return f"Generation failed: {str(e)[:300]}"


# ===============================================
# Phase 5: config.yaml generation
# ===============================================

@mcp.tool()
def generate_domain_config(domain_name: str, display_name: str, document_paths: str, workspace: str = "") -> str:
    """Auto-generates domain config.yaml.

    Args:
        domain_name: Domain name (e.g., "my-domain")
        display_name: Display name (e.g., "NSE X-Ray Inspection Equipment CS")
        document_paths: Document folder paths for indexing (comma-separated)
        workspace: Workspace name
    """
    domain_dir = _domain_dir(domain_name)
    output_path = str(domain_dir / "config.yaml")

    # document_paths may come as list or dict, so handle defensively
    if isinstance(document_paths, list):
        paths = document_paths
    elif isinstance(document_paths, dict):
        paths = document_paths.get("paths", [])
    else:
        paths = [p.strip() for p in document_paths.split(",") if p.strip()]

    try:
        sys.path.insert(0, BUILDER_PATH)
        from config_generator import generate_config, save_config, format_config_preview

        config = generate_config(
            domain_name, display_name,
            document_paths=paths, workspace=workspace
        )
        save_config(config, output_path)
        preview = format_config_preview(config)

        return f"config.yaml generated!\n- Path: {output_path}\n\n{preview}"
    except Exception as e:
        return f"Generation failed: {str(e)[:300]}"


# ===============================================
# Phase 6: Document indexing (design spec 4.1.4)
# ===============================================

@mcp.tool()
def trigger_indexing(domain_name: str) -> str:
    """Reads document paths from domains/{domain}/config.yaml and registers indexing jobs in Redis queue.

    Uses the same queue (nexus:indexing:queue) as Watchdog to unify the pipeline.
    Worker dequeues and processes asynchronously: parse -> chunk -> embed -> Qdrant store.

    Args:
        domain_name: Domain name (e.g., "my-domain")
    """
    domain_dir = _domain_dir(domain_name)
    config_path = domain_dir / "config.yaml"

    if not config_path.exists():
        return (f"Cannot find config.yaml: {config_path}\n"
                f"Run Phase 5 (generate_domain_config) first.")

    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except ImportError:
        return "PyYAML is not installed. Run pip install pyyaml and retry."
    except Exception as e:
        return f"Failed to read config.yaml: {e}"

    doc_config = config.get("documents", {})
    paths = doc_config.get("paths", [])
    extensions = doc_config.get("extensions", [".pdf", ".docx", ".xlsx", ".pptx"])

    if not paths:
        return "documents.paths is empty in config.yaml. Set the document folder paths."

    # --- File scan + Docker path conversion ---
    # Worker runs in Docker container, so convert local paths to Docker mount paths
    # docker-compose.yml: ${DOCS_PATH}:/documents:ro
    DOCKER_DOCS_ROOT = "/documents"

    files_to_index = []  # (docker_path, local_path) tuples
    path_report = []
    docs_base_path = None  # DOCS_PATH to record in .env

    for doc_path in paths:
        p = Path(doc_path)
        if not p.exists():
            path_report.append(f"- `{doc_path}` -- path not found (skipped)")
            continue

        docs_base_path = str(p)  # Use last valid path as DOCS_PATH

        found = []
        for ext in extensions:
            found.extend(p.rglob(f"*{ext}"))

        for file_path in found:
            # Local absolute path -> Docker path conversion
            relative = file_path.relative_to(p)
            docker_path = f"{DOCKER_DOCS_ROOT}/{relative.as_posix()}"
            files_to_index.append((docker_path, str(file_path)))

        path_report.append(f"- `{doc_path}` -- {len(found)} files")

    if not files_to_index:
        return (f"No files to index.\n"
                f"Paths: {paths}\nExtensions: {extensions}")

    # --- Auto-update DOCS_PATH in .env file ---
    env_updated = False
    if docs_base_path:
        try:
            env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
            if env_path.exists():
                env_content = env_path.read_text(encoding="utf-8")
                import re
                if re.search(r"^DOCS_PATH=", env_content, re.MULTILINE):
                    env_content = re.sub(
                        r"^DOCS_PATH=.*$", f"DOCS_PATH={docs_base_path}",
                        env_content, flags=re.MULTILINE
                    )
                else:
                    env_content += f"\nDOCS_PATH={docs_base_path}\n"
                env_path.write_text(env_content, encoding="utf-8")
                env_updated = True
        except Exception:
            pass  # Proceed with indexing even if .env update fails

    # --- Register in Redis queue ---
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    queue_name = "nexus:indexing:queue"

    try:
        import redis as redis_lib
        r = redis_lib.from_url(redis_url, decode_responses=True)
        r.ping()
    except ImportError:
        return "redis package is not installed. Run pip install redis and retry."
    except Exception as e:
        return f"Redis connection failed ({redis_url}): {e}"

    enqueued = 0
    for docker_path, local_path in files_to_index:
        task = {
            "file_path": docker_path,
            "retries": 0,
            "event": "domain_build",
            "domain": domain_name,
        }
        r.lpush(queue_name, json.dumps(task))
        enqueued += 1

    # --- Result report ---
    report = f"## Phase 6: Document Indexing -- Queue Registration Complete\n\n"
    report += f"**Domain:** {domain_name}\n"
    report += f"**Target extensions:** {', '.join(extensions)}\n\n"
    report += "\n".join(path_report) + "\n\n"
    report += f"**{enqueued}** jobs registered in indexing queue (`{queue_name}`).\n"
    report += f"Worker will process parse -> chunk -> embed -> Qdrant store in the background.\n\n"
    if env_updated:
        report += f"`.env` DOCS_PATH auto-updated: `{docs_base_path}`\n"
        report += "**Worker container must be restarted for new volume mount to take effect.**\n"
        report += "`docker compose up -d indexing-worker` -- indexing will start after this."

    return report


# ===============================================
# Build log save (admin use)
# ===============================================

@mcp.tool()
def save_build_log(domain_name: str, status: str, phases_completed: str, error_message: str = "") -> str:
    """Saves Domain Builder execution result as a build log.
    Call on build completion or failure.

    Args:
        domain_name: Domain name (e.g., "my-domain")
        status: Build status ("completed" or "failed")
        phases_completed: Completed Phase list (comma-separated, e.g., "1,2,3,4,5,6")
        error_message: Error message on failure
    """
    from datetime import datetime, timezone, timedelta
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)

    domain_dir = _domain_dir(domain_name)
    log_dir = domain_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "build.jsonl"

    log_entry = {
        "timestamp": now.isoformat(),
        "domain": domain_name,
        "action": "domain_build",
        "status": status,
        "phases_completed": [p.strip() for p in phases_completed.split(",") if p.strip()],
        "error": error_message
    }

    generated = []
    for fname in ["domain_knowledge.json", "skill.md", "soul.md", "config.yaml"]:
        if (domain_dir / fname).exists():
            generated.append(fname)
    log_entry["generated_files"] = generated

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return (
        f"Build log saved.\n"
        f"- Domain: {domain_name}\n"
        f"- Status: {status}\n"
        f"- Completed phases: {phases_completed}\n"
        f"- Generated files: {', '.join(generated)}"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
