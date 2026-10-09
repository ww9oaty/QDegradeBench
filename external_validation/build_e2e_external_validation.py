from __future__ import annotations
import csv, json, random, re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"e2e_testset_w_refs.csv"
OUT=ROOT/"e2e_qdegrade_24x4.csv"
TEMPLATE=ROOT/"e2e_response_collection_template.csv"
SEED=20261001

slot_re=re.compile(r"([^,]+?)\[([^\]]*)\](?:, |$)")
def parse_mr(text):
    return [(k.strip(),v.strip()) for k,v in slot_re.findall(text)]

def ascii_clean(text):
    return all(ord(ch)<128 for ch in text)

with SOURCE.open(encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f))
refs={}
for row in rows:
    refs.setdefault(row["mr"],row["ref"])
required=["name","eatType","food","priceRange","customer rating","area","familyFriendly","near"]
candidates=[]
for mr,ref in refs.items():
    pairs=parse_mr(mr)
    data=dict(pairs)
    if set(data)==set(required) and ascii_clean(mr) and ascii_clean(ref):
        candidates.append((mr,ref,data))
candidates.sort(key=lambda x:x[0])
rng=random.Random(SEED)
rng.shuffle(candidates)
selected=candidates[:24]
if len(selected)!=24:
    raise RuntimeError("Fewer than 24 eligible records")

removal_pairs=[("priceRange","customer rating"),("food","area"),("familyFriendly","near")]
field_names={"name":"name","eatType":"eat type","food":"food type","priceRange":"price range","customer rating":"customer rating","area":"area","familyFriendly":"family-friendliness","near":"nearby landmark"}
base_instruction=("Write one fluent English restaurant description that explicitly includes all of these required fields: "
                  "name, eat type, food type, price range, customer rating, area, family-friendliness, and nearby landmark. ")

def visible_data(data, omitted):
    parts=[]
    for key in required:
        if key not in omitted:
            parts.append(f"{field_names[key]}: {data[key]}")
    return "; ".join(parts)

chain_rows=[]
for idx,(mr,ref,data) in enumerate(selected,1):
    base=f"E2E{idx:02d}"
    remove=set(removal_pairs[(idx-1)%len(removal_pairs)])
    versions=[
      ("L0","A",set(),"The description will be used in a general dining guide."),
      ("L1","A",set(),""),
      ("L2","P",remove,""),
      ("L3","U",set(required),""),
    ]
    for level,ans,omitted,redundant in versions:
        if level=="L3":
            data_text="No restaurant-specific attribute values are provided."
        else:
            data_text="Restaurant data: "+visible_data(data,omitted)+"."
        prompt='Treat this as a factual data-to-text task, not creative writing. Use only the restaurant data supplied in this prompt. Do not invent any attribute values or other factual claims. If a required value is missing, explicitly identify it as unknown or ask for the missing information; do not present a fictional example as the actual description.\n\n'+base_instruction+data_text
        if redundant:
            prompt+=" "+redundant
        chain_rows.append({
          "sample_id":f"{base}_{level}","base_task_id":base,"level":level,"answerability":ans,
          "source_dataset":"E2E NLG Challenge","source_mr":mr,"source_reference":ref,
          "omitted_fields":"; ".join(field_names[x] for x in required if x in omitted),"prompt":prompt,
        })

fields=list(chain_rows[0])
with OUT.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(chain_rows)
providers=[("Model_A","") ,("Model_B","")]
with TEMPLATE.open("w",encoding="utf-8-sig",newline="") as f:
    fields2=["record_id","sample_id","base_task_id","level","answerability","provider","model","prompt","response","final_label","review_note"]
    w=csv.DictWriter(f,fieldnames=fields2); w.writeheader()
    by={r["sample_id"]:r for r in chain_rows}
    for provider,model in providers:
        for r in chain_rows:
            w.writerow({"record_id":f'{r["sample_id"]}|{provider}',"sample_id":r["sample_id"],"base_task_id":r["base_task_id"],"level":r["level"],"answerability":r["answerability"],"provider":provider,"model":model,"prompt":r["prompt"]})
print(json.dumps({"seed":SEED,"eligible_records":len(candidates),"base_tasks":len(selected),"prompts":len(chain_rows),"response_rows":len(chain_rows)*2,"output":str(OUT)},indent=2))
