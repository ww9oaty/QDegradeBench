"""Prepare a reproducible human audit: stratified 10% plus every automatic failure."""
import csv, random
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/"hotpotqa_scored_responses.csv"
OUTPUT=ROOT/"hotpotqa_human_audit.csv"
SEED=20261010

with INPUT.open(encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f))

groups=defaultdict(list)
for r in rows:
    groups[(r["provider"],r["level"])].append(r)

rng=random.Random(SEED)
selected={}
for key,group in sorted(groups.items()):
    shuffled=list(group); rng.shuffle(shuffled)
    # 32 chains per provider/level -> 4-item audit per stratum (12.5%).
    for r in shuffled[:max(1,round(len(group)*0.10))]:
        selected[r["record_id"]]=(r,"stratified_random_sample")
for r in rows:
    if r["appropriate"]!="yes" or r["json_parsed"]!="yes":
        reason=selected.get(r["record_id"],(None,""))[1]
        selected[r["record_id"]]=(r,";".join(x for x in [reason,"all_automatic_failures"] if x))

out=[]
for _,(r,reason) in sorted(selected.items()):
    out.append({
        "record_id":r["record_id"],"provider":r["provider"],"sample_id":r["sample_id"],
        "base_task_id":r["base_task_id"],"level":r["level"],"question":r["question"],
        "gold_answer":r["gold_answer"],"removed_sentence":r["removed_sentence"],
        "response":r["response"],"automatic_outcome":r["decision_outcome"],
        "audit_selection_reason":reason,"human_agrees_yes_no":"","human_outcome":"",
        "human_note":""
    })

fields=list(out[0]) if out else []
with OUTPUT.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(out)
print("audit_rows=%d source_rows=%d seed=%d"%(len(out),len(rows),SEED))
