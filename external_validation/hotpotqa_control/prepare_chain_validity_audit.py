"""Create one-row-per-chain construct-validity audit before manuscript use."""
import csv
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/"hotpotqa_32x4.csv"
OUTPUT=ROOT/"hotpotqa_chain_validity_audit.csv"

def evidence(prompt):
    marker="Evidence:\n"
    return prompt.split(marker,1)[1] if marker in prompt else prompt

with INPUT.open(encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f))
groups=defaultdict(dict)
for r in rows: groups[r["base_task_id"]][r["level"]]=r

out=[]
for base,levels in sorted(groups.items()):
    l0,l1,l2,l3=(levels[x] for x in ("L0","L1","L2","L3"))
    out.append({
        "base_task_id":base,"source_id":l0["source_id"],"question":l0["question"],
        "gold_answer":l0["gold_answer"],"L1_supporting_evidence":evidence(l1["prompt"]),
        "removed_answer_sentence":l0["removed_sentence"],
        "L2_remaining_evidence":evidence(l2["prompt"]),
        "check_1_L1_answerable_from_visible_evidence_yes_no":"",
        "check_2_L2_missing_necessary_evidence_yes_no":"",
        "check_3_question_clear_and_premise_supported_yes_no":"",
        "keep_chain_yes_no":"","exclusion_reason":"","reviewer_note":""
    })

fields=list(out[0])
with OUTPUT.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(out)
print("chain_audit_rows=%d"%len(out))
