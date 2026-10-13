"""Prepare the 128 prompts used by the exploratory white-box diagnostic."""
from __future__ import annotations
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "prompts.csv"
OUTPUT = ROOT / "data" / "probe_prompts_128.jsonl"

def main() -> None:
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    records = []
    for row in source_rows:
        answerability = row["answerability"]
        prompt = row["prompt"]
        records.append({
            "sample_id": row["sample_id"],
            "base_task": row["base_task_id"],
            "level": row["level"],
            "task_type": row["task_type"],
            "answerability": answerability,
            "binary_sufficiency": 1 if answerability == "A" else 0,
            "prompt": prompt,
            "character_count": len(prompt),
        })
    records.sort(key=lambda item: item["sample_id"])
    if len(records) != 128:
        raise RuntimeError(f"Expected 128 prompts, found {len(records)}")
    groups = Counter(item["base_task"] for item in records)
    levels = Counter(item["level"] for item in records)
    binary = Counter(item["binary_sufficiency"] for item in records)
    if len(groups) != 32 or set(groups.values()) != {4}:
        raise RuntimeError(f"Expected 32 four-level groups, found {groups}")
    if levels != Counter({"L0": 32, "L1": 32, "L2": 32, "L3": 32}):
        raise RuntimeError(f"Unexpected level counts: {levels}")
    if binary != Counter({0: 64, 1: 64}):
        raise RuntimeError(f"Unexpected binary labels: {binary}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        for item in records:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} prompts to {OUTPUT}")

if __name__ == "__main__":
    main()
