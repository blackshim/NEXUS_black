"""
Excel Structure Analyzer

Analyzes sheets, columns, data types, and row counts of Excel files
to generate a structure summary for user confirmation before JSON conversion.

Usage:
    result = analyze_excel("domain_knowledge.xlsx")
    report = format_analysis_report(result)
    print(report)  # -> Show to user for confirmation
"""

import json
import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable

_ANALYZE_SCRIPT = '''
import json, sys, openpyxl

file_path = sys.argv[1]
wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)

result = {"file_name": file_path.split("/")[-1].split("\\\\")[-1], "sheets": []}

for sname in wb.sheetnames:
    ws = wb[sname]
    rows = list(ws.iter_rows(values_only=True))

    if not rows:
        continue

    # Find header (first non-empty row)
    header_idx = None
    for i, row in enumerate(rows):
        non_empty = [c for c in row if c is not None and str(c).strip()]
        if len(non_empty) >= 2:
            header_idx = i
            break

    if header_idx is None:
        continue

    headers = []
    for c in rows[header_idx]:
        h = str(c).strip() if c else ""
        headers.append(h)

    # Count data rows (after header)
    data_rows = []
    for row in rows[header_idx + 1:]:
        cells = [c for c in row if c is not None and str(c).strip()]
        if cells:
            data_rows.append(row)

    # Per-column analysis
    columns = []
    for col_idx, header in enumerate(headers):
        if not header:
            continue

        values = []
        for row in data_rows:
            if col_idx < len(row) and row[col_idx] is not None:
                values.append(row[col_idx])

        # Infer data type
        num_count = sum(1 for v in values if isinstance(v, (int, float)))
        str_count = sum(1 for v in values if isinstance(v, str))

        if num_count > str_count:
            dtype = "numeric"
        else:
            dtype = "text"

        # Sample values (first 3)
        samples = [str(v)[:50] for v in values[:3]]

        columns.append({
            "name": header,
            "type": dtype,
            "non_empty": len(values),
            "total": len(data_rows),
            "samples": samples
        })

    sheet_info = {
        "name": sname,
        "header_row": header_idx + 1,
        "data_rows": len(data_rows),
        "columns": columns
    }
    result["sheets"].append(sheet_info)

wb.close()
json.dump(result, sys.stdout, ensure_ascii=False)
'''


def analyze_excel(file_path: str) -> dict:
    """Analyzes the structure of an Excel file.

    Returns:
        {
            "file_name": "xxx.xlsx",
            "sheets": [
                {
                    "name": "sheet name",
                    "header_row": 2,
                    "data_rows": 10,
                    "columns": [{"name": "column name", "type": "text", "non_empty": 8, ...}]
                }
            ]
        }
    """
    if not Path(file_path).exists():
        return {"error": f"File not found: {file_path}"}

    proc = subprocess.run(
        [PYTHON, "-c", _ANALYZE_SCRIPT, file_path],
        capture_output=True, text=True, timeout=60,
        stdin=subprocess.DEVNULL
    )

    if proc.returncode != 0:
        return {"error": proc.stderr.strip()[:300]}

    return json.loads(proc.stdout)


def format_analysis_report(analysis: dict) -> str:
    """Converts analysis results into a markdown report for display to the user."""
    if "error" in analysis:
        return f"Analysis failed: {analysis['error']}"

    report = f"## Excel Structure Analysis: {analysis['file_name']}\n\n"
    report += f"**Number of sheets:** {len(analysis['sheets'])}\n\n"

    for sheet in analysis["sheets"]:
        report += f"### Sheet: {sheet['name']}\n"
        report += f"- Header row: row {sheet['header_row']}\n"
        report += f"- Data rows: {sheet['data_rows']}\n"
        report += f"- Number of columns: {len(sheet['columns'])}\n\n"

        report += "| Column Name | Type | Filled Rows | Samples |\n"
        report += "|-------------|------|-------------|----------|\n"
        for col in sheet["columns"]:
            samples = ", ".join(col["samples"][:2]) if col["samples"] else "-"
            report += f"| {col['name']} | {col['type']} | {col['non_empty']}/{col['total']} | {samples[:40]} |\n"
        report += "\n"

    report += "---\n"
    report += "**Proceed with generating JSON from this structure?**\n"

    return report
