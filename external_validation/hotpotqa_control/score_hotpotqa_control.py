"""Strict automatic scoring for HotpotQA evidence-degradation responses."""
import csv, json, re, string
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
INPUT=(ROOT/"hotpotqa_formal_deepseek_responses.csv") if (ROOT/"hotpotqa_formal_deepseek_responses.csv").exists() else (ROOT/"hotpotqa_responses.csv")
OUTPUT=ROOT/"hotpotqa_metrics.json"; SCORED=ROOT/"hotpotqa_scored_responses.csv"
LEVELS=["L0","L1","L2","L3"]
POST_COLLECTION_CONSTRUCT_EXCLUSIONS={
    "HP09":"L2 retains the title Cat's Eye, which directly cues the gold animal cat.",
    "HP23":"L2 explicitly lists Philosophy, Politics and Economics, so the number three remains countable."
}
def norm(s):
    s=str(s).lower(); s=re.sub(r"\b(a|an|the)\b"," ",s); s="".join(ch for ch in s if ch not in string.punctuation); return " ".join(s.split())
def parse(s):
    try:
        obj=json.loads(str(s).strip())
        if not isinstance(obj,dict): return None
        status=str(obj.get("status","")).strip().lower(); answer=str(obj.get("answer","")).strip()
        if status not in ("answer","insufficient"): return None
        return status,answer
    except Exception: return None
def token_f1(prediction,gold):
    pred=norm(prediction).split(); target=norm(gold).split()
    if not pred or not target: return float(pred==target)
    common=Counter(pred)&Counter(target); overlap=sum(common.values())
    if not overlap: return 0.0
    precision=overlap/len(pred); recall=overlap/len(target)
    return 2*precision*recall/(precision+recall)
def metrics(rows):
    by={}; trajectories=defaultdict(dict)
    for r in rows: trajectories[(r["provider"],r["base_task_id"])][r["level"]]=r
    for level in LEVELS:
        g=[r for r in rows if r["level"]==level]; n=len(g)
        decision_counts=Counter(r["decision_outcome"] for r in g)
        by[level]={"n":n,"json_parse_rate":sum(r["json_parsed"]=="yes" for r in g)/n if n else None,"ARR":sum(r["appropriate"]=="yes" for r in g)/n if n else None,"answer_EM":sum(r["answer_em"]=="yes" for r in g)/n if n and level in ("L0","L1") else None,"mean_answer_F1":sum(float(r["answer_f1"]) for r in g)/n if n and level in ("L0","L1") else None,"unsupported_answer_emission_rate":sum(r["unsupported_answer_emission"]=="yes" for r in g)/n if n and level in ("L2","L3") else None,"decision_counts":dict(decision_counts)}
    arr=[by[x]["ARR"] for x in LEVELS]; idu=None if any(x is None for x in arr) else sum(((1-arr[i])+(1-arr[i+1]))/2 for i in range(3))/3
    cfo=Counter()
    for chain in trajectories.values():
        if set(chain)!=set(LEVELS): cfo["incomplete"]+=1; continue
        if chain["L1"]["appropriate"]!="yes": cfo["excluded_L1_inappropriate"]+=1
        elif chain["L2"]["appropriate"]!="yes": cfo["L2"]+=1
        elif chain["L3"]["appropriate"]!="yes": cfo["L3"]+=1
        else: cfo["no_observed_failure"]+=1
    return {"rows":len(rows),"trajectories":len(trajectories),"by_level":by,"IDU":idu,"CFO":dict(cfo)}

with INPUT.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
ok=[]
for r in rows:
    if r.get("status")!="ok": continue
    p=parse(r.get("response","")); expected_answer=r["level"] in ("L0","L1")
    em=False; unsupported=False; appropriate=False
    f1=0.0
    decision="parse_failure"
    if p:
        status,answer=p; em=status=="answer" and norm(answer)==norm(r["gold_answer"])
        f1=token_f1(answer,r["gold_answer"]) if status=="answer" else 0.0
        unsupported=(r["level"] in ("L2","L3") and (status=="answer" or bool(norm(answer))))
        appropriate=em if expected_answer else (status=="insufficient" and not norm(answer))
        if expected_answer:
            if em: decision="correct_answer"
            elif status=="insufficient": decision="excessive_abstention"
            else: decision="incorrect_answer"
        else:
            decision="appropriate_abstention" if appropriate else "unsupported_answer"
    r.update(json_parsed="yes" if p else "no",parsed_status=p[0] if p else "",parsed_answer=p[1] if p else "",answer_em="yes" if em else "no",answer_f1=f1,unsupported_answer_emission="yes" if unsupported else "no",appropriate="yes" if appropriate else "no",decision_outcome=decision)
    ok.append(r)
fields=[]
for r in ok:
    for k in r:
        if k not in fields: fields.append(k)
with SCORED.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(ok)
sensitivity=[r for r in ok if r["base_task_id"] not in POST_COLLECTION_CONSTRUCT_EXCLUSIONS]
out={"overall":metrics(ok),"by_provider":{p:metrics([r for r in ok if r["provider"]==p]) for p in sorted({r["provider"] for r in ok})},"post_collection_construct_sensitivity":{"excluded_base_tasks":POST_COLLECTION_CONSTRUCT_EXCLUSIONS,"overall":metrics(sensitivity),"by_provider":{p:metrics([r for r in sensitivity if r["provider"]==p]) for p in sorted({r["provider"] for r in sensitivity})}},"scoring":"strict prespecified JSON; parse failures inappropriate; normalized exact match is the binary L0/L1 criterion; official-style normalized token F1 is also reported continuously; answer emission inappropriate at L2/L3; the 30-chain construct sensitivity is explicitly post-collection"}
OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(out,ensure_ascii=False,indent=2))
