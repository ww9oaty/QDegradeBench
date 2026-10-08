# -*- coding: utf-8 -*-
"""Compute E2E external validation metrics from the annotation sheet.

Same definitions as the main experiment
(QDegradeBench_reproducibility_package/analysis/reproduce_metrics.py):
label counts, ARR by level, UAR, IDU, CFO, optional double-review
agreement + Cohen's kappa. Results are reported overall and per provider.

Labels must be filled in e2e_annotation_sheet.csv (final_label column,
one of CA/PA/CQ/AI/UA/IR). This script never invents labels.

Usage: python compute_e2e_metrics.py [annotation_csv]
"""
import csv, json, sys, io
from collections import Counter, defaultdict
from pathlib import Path

if __name__ == "__main__" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
ANNOTATION = ROOT / "e2e_annotation_sheet.csv"
LABELS = ["CA", "PA", "CQ", "AI", "UA", "IR"]
LEVELS = ["L0", "L1", "L2", "L3"]


def appropriate(answerability, label):
    allowed = {"A": {"CA"}, "P": {"CA", "PA", "CQ", "AI"}, "U": {"PA", "CQ", "AI"}}
    return label in allowed.get(answerability, set())


def cohen_kappa(pairs):
    n = len(pairs)
    if not n:
        return None, None
    observed = sum(a == b for a, b in pairs) / n
    c1 = Counter(a for a, _ in pairs)
    c2 = Counter(b for _, b in pairs)
    expected = sum((c1[x] / n) * (c2[x] / n) for x in LABELS)
    if expected == 1:
        return observed, None
    return observed, (observed - expected) / (1 - expected)


def group_metrics(rows, label_field="final_label"):
    rows = [dict(r, **{label_field: r.get(label_field, "").strip()}) for r in rows]
    seen = set()
    for r in rows:
        key = (r["provider"], r.get("requested_model", ""), r["base_task_id"], r["level"])
        if key in seen:
            raise ValueError("Duplicate trajectory-level record: " + str(key))
        seen.add(key)
        if r["level"] not in LEVELS or r["answerability"] not in ("A", "P", "U"):
            raise ValueError("Invalid level or answerability")
        if r[label_field] and r[label_field] not in LABELS:
            raise ValueError("Invalid label: " + r[label_field])
    labeled = [r for r in rows if r[label_field] in LABELS]
    level_results = {}
    for lvl in LEVELS:
        lr = [r for r in labeled if r["level"] == lvl]
        counts = Counter(r[label_field] for r in lr)
        arr = (sum(appropriate(r["answerability"], r[label_field]) for r in lr) / len(lr)
               if lr else None)
        u_rows = [r for r in lr if r["answerability"] == "U"]
        uar = (None if not u_rows
               else sum(r[label_field] == "UA" for r in u_rows) / len(u_rows))
        level_results[lvl] = {"n_labeled": len(lr), "labels": dict(counts),
                              "ARR": arr, "UAR": uar}
    arrs = [level_results[l]["ARR"] for l in LEVELS]
    idu = None
    if len(labeled) == len(rows) and all(a is not None for a in arrs):
        u = [1 - a for a in arrs]
        idu = sum((u[i] + u[i + 1]) / 2 for i in range(3)) / 3
    trajectories = defaultdict(dict)
    for r in rows:
        trajectories[(r["provider"], r.get("requested_model", ""), r["base_task_id"])][r["level"]] = r
    cfo = Counter()
    for chain in trajectories.values():
        if set(chain) != set(LEVELS) or any(r[label_field] not in LABELS for r in chain.values()):
            cfo["incomplete_chain"] += 1
        elif not appropriate(chain["L1"]["answerability"], chain["L1"][label_field]):
            cfo["excluded_L1_inappropriate"] += 1
        elif not appropriate(chain["L2"]["answerability"], chain["L2"][label_field]):
            cfo["L2"] += 1
        elif not appropriate(chain["L3"]["answerability"], chain["L3"][label_field]):
            cfo["L3"] += 1
        else:
            cfo["no_observed_failure"] += 1
    if any(set(chain) != set(LEVELS) for chain in trajectories.values()):
        idu = None
    return {
        "analysis_status": "complete" if rows and len(labeled) == len(rows) and all(set(c) == set(LEVELS) for c in trajectories.values()) else "incomplete",
        "CFO_eligible": sum(cfo[k] for k in ("L2", "L3", "no_observed_failure")),
        "rows": len(rows),
        "labeled": len(labeled),
        "unlabeled": len(rows) - len(labeled),
        "by_level": level_results,
        "IDU": idu,
        "CFO": dict(cfo),
        "trajectories": len(trajectories),
    }


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ANNOTATION
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    print("annotation rows:", len(rows))
    out = {"overall": group_metrics(rows), "by_provider": {}}
    providers = sorted(set(r["provider"] for r in rows))
    for p in providers:
        out["by_provider"][p] = group_metrics([r for r in rows if r["provider"] == p])
    if rows and all(k in rows[0] for k in ("primary_human_label", "second_human_label")):
        pairs = [(r["primary_human_label"], r["second_human_label"]) for r in rows
                 if r.get("primary_human_label", "").strip() in LABELS
                 and r.get("second_human_label", "").strip() in LABELS]
        ag, kappa = cohen_kappa(pairs)
        out["double_review"] = {"n": len(pairs), "agreement": ag, "cohen_kappa": kappa}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if out["overall"]["labeled"] == 0:
        print("\nNO LABELS YET: fill final_label (CA/PA/CQ/AI/UA/IR) in "
              "e2e_annotation_sheet.csv, then re-run this script.")
    elif out["overall"]["unlabeled"]:
        print("\nWARN: %d rows still unlabeled; metrics computed on labeled rows only."
              % out["overall"]["unlabeled"])


if __name__ == "__main__":
    main()
