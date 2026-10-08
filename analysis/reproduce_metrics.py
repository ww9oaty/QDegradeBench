from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(name):
    with (ROOT / name).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def appropriate(answerability, label):
    allowed = {
        "A": {"CA"},
        "P": {"CA", "PA", "CQ", "AI"},
        "U": {"PA", "CQ", "AI"},
    }
    return label in allowed[answerability]


def cohen_kappa(pairs):
    labels = ["CA", "PA", "CQ", "AI", "UA", "IR"]
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    c1 = Counter(a for a, _ in pairs)
    c2 = Counter(b for _, b in pairs)
    expected = sum((c1[x] / n) * (c2[x] / n) for x in labels)
    return observed, (observed - expected) / (1 - expected)


responses = read_csv("responses.csv")
reviews = read_csv("double_review_sample.csv")
assert len(responses) == 512
assert len(reviews) == 128

levels = ["L0", "L1", "L2", "L3"]
level_results = {}
for level in levels:
    rows = [r for r in responses if r["level"] == level]
    counts = Counter(r["final_label"] for r in rows)
    arr = sum(appropriate(r["answerability"], r["final_label"]) for r in rows) / len(rows)
    u_rows = [r for r in rows if r["answerability"] == "U"]
    uar = None if not u_rows else sum(r["final_label"] == "UA" for r in u_rows) / len(u_rows)
    level_results[level] = {"n": len(rows), "labels": dict(counts), "ARR": arr, "UAR": uar}

u = [1 - level_results[level]["ARR"] for level in levels]
idu = sum((u[i] + u[i + 1]) / 2 for i in range(3)) / 3

trajectories = defaultdict(dict)
for r in responses:
    trajectories[(r["provider"], r["base_task_id"])][r["level"]] = r
assert len(trajectories) == 128
cfo = Counter()
for chain in trajectories.values():
    if not appropriate(chain["L2"]["answerability"], chain["L2"]["final_label"]):
        cfo["L2"] += 1
    elif not appropriate(chain["L3"]["answerability"], chain["L3"]["final_label"]):
        cfo["L3"] += 1
    else:
        cfo["no_observed_failure"] += 1

pairs = [(r["primary_human_label"], r["second_human_label"]) for r in reviews]
agreement, kappa = cohen_kappa(pairs)

result = {
    "row_count": len(responses),
    "trajectory_count": len(trajectories),
    "by_level": level_results,
    "IDU": idu,
    "CFO": dict(cfo),
    "double_review": {"n": len(pairs), "agreement": agreement, "cohen_kappa": kappa},
}
print(json.dumps(result, ensure_ascii=False, indent=2))

assert [round(level_results[x]["ARR"], 4) for x in levels] == [0.9844, 1.0, 0.7812, 0.7266]
assert round(level_results["L3"]["UAR"], 4) == 0.2823
assert round(idu, 4) == 0.1211
assert cfo == Counter({"no_observed_failure": 80, "L2": 28, "L3": 20})
assert round(agreement, 4) == 0.7344
assert round(kappa, 3) == 0.567
