"""
Excel -> JSON Converter

Converts Excel data to domain_knowledge.json based on analyze_excel() results.
Automatically assigns metadata and usage_stats initial values during conversion.

Usage:
    analysis = analyze_excel("domain_knowledge.xlsx")
    # After user confirmation...
    result = convert_excel_to_json(
        file_path="domain_knowledge.xlsx",
        output_path="domains/my-domain/domain_knowledge.json",
        domain_name="my-domain"
    )
"""

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PYTHON = sys.executable
KST = timezone(timedelta(hours=9))

_CONVERT_SCRIPT = '''
import json, sys, openpyxl
from datetime import datetime

args = json.loads(sys.argv[1])
file_path = args["file_path"]
domain_name = args["domain_name"]
skip_sheets = args.get("skip_sheets", [])

wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)

items = []
item_id = 0
now = datetime.now().isoformat()

for sname in wb.sheetnames:
    # Skip specified sheets
    if sname in skip_sheets:
        continue

    ws = wb[sname]
    rows = list(ws.iter_rows(values_only=True))

    if not rows:
        continue

    # Find header
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
        h = str(c).strip().replace("\\n", " ") if c else ""
        headers.append(h)

    # Process data rows
    for row in rows[header_idx + 1:]:
        cells = [str(c).strip() if c is not None else "" for c in row]

        # Skip completely empty rows
        if not any(c for c in cells if c):
            continue

        item_id += 1
        item = {
            "id": f"{domain_name.upper().replace('-','_')}-{item_id:04d}",
            "source": "excel_import",
            "created_at": now,
            "created_by": "domain_builder",
            "category": sname,
            "usage_stats": {
                "suggested": 0,
                "resolved": 0,
                "failed": 0,
                "success_rate": 0
            }
        }

        for h_idx, header in enumerate(headers):
            if not header or h_idx >= len(cells) or not cells[h_idx]:
                continue

            # Korean header -> English key mapping (per design doc section 4.1.3)
            # Keys are Korean Excel header values (functional — must match actual spreadsheet headers)
            HEADER_MAP = {
                # error_code: "에러코드/에러 코드/오류코드/코드" = error code
                "에러코드": "error_code", "에러 코드": "error_code", "오류코드": "error_code",
                # description: "코드 내용/코드내용" = code description, "설명" = explanation, "내용" = content
                "코드": "error_code", "코드 내용": "description", "코드내용": "description",
                # symptom: "증상" = symptom
                "증상": "symptom", "설명": "description", "내용": "description",
                # cause: "원인" = cause, "원인분석" = cause analysis
                "원인": "cause", "원인분석": "cause",
                # solution: "해결/해결방법" = solution, "조치/조치방법" = action/remedy
                "해결": "solution", "해결방법": "solution", "해결 방법": "solution",
                "조치": "solution", "조치방법": "solution", "조치 방법": "solution",
                # response_type: "대응/대응분류" = response type/classification
                "대응": "response_type", "대응분류": "response_type", "대응 분류": "response_type",
                # phone_action: "전화/전화조치" = phone action/remedy
                "전화": "phone_action", "전화조치": "phone_action", "전화 조치": "phone_action",
                # visit_action: "방문/방문조치" = on-site visit action/remedy
                "방문": "visit_action", "방문조치": "visit_action", "방문 조치": "visit_action",
                # preparation: "준비물" = required materials, "준비" = preparation
                "준비물": "preparation", "준비": "preparation",
                # note: "비고" = remarks, "참고" = reference, "메모" = memo
                "비고": "note", "참고": "note", "메모": "note",
                # category: "카테고리" = category, "분류" = classification
                "카테고리": "category", "분류": "category",
                # model: "모델" = model, "장비" = equipment, "장비모델" = equipment model
                "모델": "model", "장비": "model", "장비모델": "model",
                # assignee: "담당" = in charge, "담당자" = person in charge
                "담당": "assignee", "담당자": "assignee",
                # status: "상태" = status, "현재상태" = current status
                "상태": "status", "현재상태": "current_status",
                # tags: "태그" = tags
                "태그": "tags",
            }

            # Skip meaningless sequence/number columns (Korean + English)
            # Korean keys: "순번" = sequence number, "번호" = number, "일련번호" = serial number
            SKIP_HEADERS = {
                "no", "no.", "no_", "순번", "번호", "#",
                "일련번호", "seq", "index", "idx",
            }

            header_lower = header.lower().strip()

            if header_lower in SKIP_HEADERS:
                continue

            if header_lower in HEADER_MAP:
                key = HEADER_MAP[header_lower]
            else:
                # If no mapping, convert to lowercase + underscore
                key = header_lower.replace(" ", "_").replace("/", "_")
                key = "".join(c for c in key if c.isalnum() or c == "_")

            if key in SKIP_HEADERS:
                continue

            item[key] = cells[h_idx]

        # Only add items with meaningful data
        data_fields = [k for k in item.keys() if k not in
                       ("id", "source", "created_at", "created_by", "category", "usage_stats")]
        if data_fields:
            items.append(item)

wb.close()

# Result JSON structure
output = {
    "_meta": {
        "domain": domain_name,
        "schema_version": 1,
        "last_crystallized": now,
        "stats": {
            "total_items": len(items),
            "from_excel": len(items),
            "from_conversation": 0,
            "from_suggestion": 0
        },
        "source_file": file_path.split("/")[-1].split("\\\\")[-1]
    },
    "items": items
}

json.dump(output, sys.stdout, ensure_ascii=False)
'''


def convert_excel_to_json(
    file_path: str,
    output_path: str,
    domain_name: str,
    skip_sheets: list[str] = None
) -> dict:
    """Converts Excel to domain_knowledge.json.

    Args:
        file_path: Excel file path
        output_path: Output JSON path
        domain_name: Domain name (e.g., "my-domain")
        skip_sheets: List of sheet names to skip

    Returns:
        {"status": "ok", "total_items": N, "output_path": "..."}
    """
    if not Path(file_path).exists():
        return {"error": f"File not found: {file_path}"}

    args = json.dumps({
        "file_path": file_path,
        "domain_name": domain_name,
        "skip_sheets": skip_sheets or []
    })

    proc = subprocess.run(
        [PYTHON, "-c", _CONVERT_SCRIPT, args],
        capture_output=True, text=True, timeout=120,
        stdin=subprocess.DEVNULL
    )

    if proc.returncode != 0:
        return {"error": proc.stderr.strip()[:300]}

    data = json.loads(proc.stdout)

    # Create output directory
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "status": "ok",
        "total_items": len(data.get("items", [])),
        "output_path": output_path,
        "sheets": len(data.get("_meta", {}).get("stats", {}))
    }
