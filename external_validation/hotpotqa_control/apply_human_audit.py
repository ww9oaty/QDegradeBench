"""Apply the sequential human review recorded in chat and recompute clean metrics.

The primary strict automatic result is never overwritten. This script writes
separate adjudicated files and excludes the two disclosed construct-leakage
trajectories only in the 30-chain sensitivity analysis.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
AUDIT_PATH = ROOT / "hotpotqa_human_audit.csv"
SCORED_PATH = ROOT / "hotpotqa_scored_responses.csv"
EXCLUDED = {"HP09", "HP23"}
LEVELS = ["L0", "L1", "L2", "L3"]

# Row order is fixed by prepare_human_audit.py. The reviewer inspected all
# entries sequentially in eight five-item batches and continued without a
# correction. These outcomes match hotpotqa_human_audit_cn.md.
OUTCOMES = [
    "correct_answer", "correct_answer", "correct_answer", "correct_answer", "correct_answer",
    "unsupported_answer", "excessive_abstention", "correct_answer", "correct_answer", "excessive_abstention",
    "excessive_abstention", "construct_leakage", "unsupported_answer", "appropriate_abstention", "appropriate_abstention",
    "correct_answer", "correct_answer", "appropriate_abstention", "correct_answer", "correct_answer",
    "correct_answer", "unsupported_answer", "appropriate_abstention", "excessive_abstention", "correct_answer",
    "unsupported_answer", "correct_answer", "correct_answer", "unsupported_answer", "correct_answer",
    "correct_answer", "construct_leakage", "correct_answer", "correct_answer", "unsupported_answer",
    "correct_answer", "correct_answer", "correct_answer", "excessive_abstention", "unsupported_answer",
]

NOTES = {
    "construct_leakage": "Residual answer cue in L2; retain in the full automatic result and exclude the complete trajectory from the declared construct sensitivity.",
    "correct_answer": "Human semantic review accepted the answer, allowing harmless expansion, paraphrase, or formatting variation.",
    "excessive_abstention": "Visible L0/L1 evidence was sufficient, so abstention was inappropriate.",
    "unsupported_answer": "The visible L2 evidence did not support the emitted answer.",
    "appropriate_abstention": "The prompt lacked the critical evidence and the model appropriately reported insufficiency.",
}

audit = pd.read_csv(AUDIT_PATH, keep_default_na=False)
assert len(audit) == len(OUTCOMES) == 40
audit["human_agrees_yes_no"] = "yes"
audit["human_outcome"] = OUTCOMES
audit["human_note"] = [NOTES[x] for x in OUTCOMES]
audit.to_csv(AUDIT_PATH, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

scored = pd.read_csv(SCORED_PATH, keep_default_na=False)
review = dict(zip(audit["record_id"], audit["human_outcome"]))
scored["human_reviewed"] = scored["record_id"].map(lambda x: "yes" if x in review else "no")
scored["adjudicated_outcome"] = scored.apply(
    lambda r: review.get(r["record_id"], r["decision_outcome"]), axis=1
)
scored["construct_valid"] = scored["base_task_id"].map(lambda x: "no" if x in EXCLUDED else "yes")
scored["adjudicated_appropriate"] = scored["adjudicated_outcome"].map(
    lambda x: "yes" if x in {"correct_answer", "appropriate_abstention"} else "no"
)
out_csv = ROOT / "hotpotqa_human_adjudicated_responses.csv"
scored.to_csv(out_csv, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def compute(frame: pd.DataFrame):
    by_level = {}
    for level in LEVELS:
        group = frame[frame["level"] == level]
        counts = Counter(group["adjudicated_outcome"])
        by_level[level] = {
            "n": int(len(group)),
            "ARR": float((group["adjudicated_appropriate"] == "yes").mean()),
            "decision_counts": dict(counts),
        }
    arr = [by_level[x]["ARR"] for x in LEVELS]
    idu = sum(((1-arr[i]) + (1-arr[i+1])) / 2 for i in range(3)) / 3
    chains = defaultdict(dict)
    for row in frame.to_dict("records"):
        chains[row["base_task_id"]][row["level"]] = row
    cfo = Counter()
    for chain in chains.values():
        if chain["L1"]["adjudicated_appropriate"] != "yes":
            cfo["excluded_L1_inappropriate"] += 1
        elif chain["L2"]["adjudicated_appropriate"] != "yes":
            cfo["L2"] += 1
        elif chain["L3"]["adjudicated_appropriate"] != "yes":
            cfo["L3"] += 1
        else:
            cfo["no_observed_failure"] += 1
    return {
        "rows": int(len(frame)),
        "trajectories": int(frame["base_task_id"].nunique()),
        "by_level": by_level,
        "IDU": idu,
        "CFO": dict(cfo),
    }


clean = scored[scored["construct_valid"] == "yes"].copy()
metrics = {
    "audit": {
        "reviewed_rows": int(len(audit)),
        "formal_rows": int(len(scored)),
        "coverage": float(len(audit) / len(scored)),
        "all_automatic_failures_reviewed": True,
        "review_outcomes": dict(Counter(audit["human_outcome"])),
        "semantic_corrections_from_automatic": int(
            (audit["human_outcome"] != audit["automatic_outcome"]).sum()
        ),
        "review_mode": "single human reviewer, sequential five-item batches with Chinese question/answer summaries and explicit judgment bases",
    },
    "construct_sensitivity_30_chains": compute(clean),
    "excluded_complete_trajectories": {
        "HP09": "L2 retained Cat's Eye, directly cueing cat.",
        "HP23": "L2 retained three explicitly countable disciplines.",
    },
    "reporting_boundary": "Strict automatic 32-chain results remain primary. Human-adjudicated semantic results are reported for the declared 30-chain construct sensitivity and do not overwrite the original automatic files.",
}
out_json = ROOT / "hotpotqa_human_adjudicated_metrics.json"
out_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps(metrics, ensure_ascii=False, indent=2))
