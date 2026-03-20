"""
Crystallization Scheduler

Executes weekly/monthly tasks according to Design Doc 4.2.7 Crystallization cycle.

Weekly tasks:
- Check promotion criteria -> auto-reflect in skill.md
- Generate weekly report

Monthly tasks:
- Monthly report + JSON -> Excel export

Realtime tasks (log saving, field extraction, usage_stats) are controlled by skill.md during conversations.

Usage:
    # Run weekly task (manual or cron/Task Scheduler)
    python scheduler.py weekly --domains-base /path/to/domains

    # Run monthly task
    python scheduler.py monthly --domains-base /path/to/domains

    # Specific domain only
    python scheduler.py weekly --domains-base /path/to/domains --domain my-domain
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))


def discover_domains(domains_base: str) -> list[str]:
    """Returns a list of domains under domains/."""
    base = Path(domains_base)
    if not base.exists():
        return []
    return [
        d.name for d in base.iterdir()
        if d.is_dir() and (d / "config.yaml").exists()
    ]


def run_weekly(domains_base: str, domain_name: str) -> dict:
    """Weekly task: promotion + report generation."""
    domain_dir = Path(domains_base) / domain_name
    knowledge_path = str(domain_dir / "domain_knowledge.json")
    skill_path = str(domain_dir / "skill.md")
    log_dir = str(domain_dir / "logs")
    reports_dir = domain_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    results = {"domain": domain_name, "tasks": []}

    # 1. Auto-promotion
    try:
        from promoter import auto_promote
        promote_result = auto_promote(knowledge_path, skill_path)
        results["tasks"].append({
            "task": "auto_promote",
            "promoted": promote_result.get("promoted", 0),
            "items": promote_result.get("items", [])
        })
    except Exception as e:
        results["tasks"].append({"task": "auto_promote", "error": str(e)})

    # 2. Generate weekly report
    try:
        from reporter import generate_weekly_report
        report = generate_weekly_report(knowledge_path, log_dir, domain_name)

        now = datetime.now(KST)
        report_path = reports_dir / f"weekly_{now.strftime('%Y-%m-%d')}.md"
        report_path.write_text(report, encoding='utf-8')

        results["tasks"].append({
            "task": "weekly_report",
            "path": str(report_path)
        })
    except Exception as e:
        results["tasks"].append({"task": "weekly_report", "error": str(e)})

    return results


def run_monthly(domains_base: str, domain_name: str) -> dict:
    """Monthly task: report + Excel export."""
    domain_dir = Path(domains_base) / domain_name
    knowledge_path = str(domain_dir / "domain_knowledge.json")
    log_dir = str(domain_dir / "logs")
    exports_dir = str(domain_dir / "exports")
    reports_dir = domain_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    results = {"domain": domain_name, "tasks": []}

    # 1. Monthly report + Excel export
    try:
        from reporter import generate_monthly_report
        monthly = generate_monthly_report(
            knowledge_path, log_dir, exports_dir, domain_name
        )

        now = datetime.now(KST)
        report_path = reports_dir / f"monthly_{now.strftime('%Y-%m')}.md"
        report_path.write_text(monthly["report"], encoding='utf-8')

        results["tasks"].append({
            "task": "monthly_report",
            "path": str(report_path),
            "export": monthly.get("export_result", {})
        })
    except Exception as e:
        results["tasks"].append({"task": "monthly_report", "error": str(e)})

    return results


def main():
    parser = argparse.ArgumentParser(description="NEXUS Crystallization Scheduler")
    parser.add_argument("action", choices=["weekly", "monthly"],
                        help="Task type to execute")
    parser.add_argument("--domains-base", required=True,
                        help="Path to the domains/ folder")
    parser.add_argument("--domain", default="",
                        help="Run for a specific domain only (all domains if unspecified)")

    args = parser.parse_args()

    # Add module path
    sys.path.insert(0, str(Path(__file__).parent))

    domains_base = args.domains_base
    if args.domain:
        domains = [args.domain]
    else:
        domains = discover_domains(domains_base)

    if not domains:
        print(f"No domains found: {domains_base}")
        sys.exit(1)

    print(f"[{datetime.now(KST).isoformat()}] Starting {args.action} task")
    print(f"Target domains: {', '.join(domains)}")

    all_results = []
    for domain in domains:
        print(f"\n--- {domain} ---")
        if args.action == "weekly":
            result = run_weekly(domains_base, domain)
        else:
            result = run_monthly(domains_base, domain)

        all_results.append(result)
        for task in result.get("tasks", []):
            if "error" in task:
                print(f"  [FAIL] {task['task']}: {task['error']}")
            else:
                print(f"  [OK] {task['task']}: {task.get('path', task.get('promoted', ''))}")

    print(f"\nComplete: {len(all_results)} domain(s) processed")


if __name__ == "__main__":
    main()
