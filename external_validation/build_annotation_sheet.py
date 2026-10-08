# -*- coding: utf-8 -*-
"""Build the human-review annotation sheet for the E2E external validation.

Joins the collected responses (e2e_model_responses.csv) with the prompt
metadata (e2e_qdegrade_24x4.csv). Label columns are left empty for the
annotator. Output: e2e_annotation_sheet.csv (utf-8-sig for Excel).
"""
import csv, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
RESP = ROOT / "e2e_model_responses.csv"
PROMPTS = ROOT / "e2e_qdegrade_24x4.csv"
OUT = ROOT / "e2e_annotation_sheet.csv"

prompts = {}
with PROMPTS.open(encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        prompts[r["sample_id"]] = r

rows = []
with RESP.open(encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        if r["status"] != "ok":
            continue
        p = prompts[r["sample_id"]]
        rows.append({
            "record_id": r["record_id"],
            "sample_id": r["sample_id"],
            "base_task_id": r["base_task_id"],
            "level": r["level"],
            "answerability": r["answerability"],
            "provider": r["provider"],
            "requested_model": r["requested_model"],
            "source_mr": p.get("source_mr", ""),
            "source_reference": p.get("source_reference", ""),
            "omitted_fields": p.get("omitted_fields", ""),
            "prompt": r["prompt"],
            "response": r["response"],
            "final_label": "",
            "review_note": "",
        })

order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
rows.sort(key=lambda r: (r["provider"], r["base_task_id"], order[r["level"]]))

fields = ["record_id", "sample_id", "base_task_id", "level", "answerability",
          "provider", "requested_model", "source_mr", "source_reference",
          "omitted_fields", "prompt", "response", "final_label", "review_note"]
with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
print("annotation rows written:", len(rows))
print("output:", OUT)
