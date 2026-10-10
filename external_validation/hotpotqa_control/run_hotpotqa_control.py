"""Resumable two-endpoint collection for the HotpotQA control."""
import argparse, csv, json, os, random, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "hotpotqa_32x4.csv"
HISTORY = ROOT / "hotpotqa_responses.jsonl"
OUTPUT = ROOT / "hotpotqa_responses.csv"
META = ROOT / "hotpotqa_run_metadata.json"
SYSTEM = "You are a careful evidence-bounded question answering assistant."
PROVIDERS = {
 "Qwen-DashScope": {"model":"qwen3.7-plus", "endpoint":"https://ws-79jw3e4iorb8fgf8.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions", "env":"DASHSCOPE_API_KEY", "extra":{"enable_thinking":False}},
 "DeepSeek-Official": {"model":"deepseek-v4-pro", "endpoint":"https://api.deepseek.com/chat/completions", "env":"DEEPSEEK_API_KEY", "extra":{"thinking":{"type":"disabled"}}},
}

def now(): return datetime.now(timezone.utc).isoformat()

def call(p, key, prompt):
    body={"model":p["model"],"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],"temperature":0,"max_tokens":256}
    body.update(p["extra"]); payload=json.dumps(body).encode()
    for attempt in range(5):
        req=urllib.request.Request(p["endpoint"],data=payload,headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=180) as resp:
                data=json.load(resp); ch=data["choices"][0]; usage=data.get("usage") or {}
                return {"status":"ok","response":ch["message"].get("content", ""),"reported_model":data.get("model", ""),"finish_reason":ch.get("finish_reason", ""),"input_tokens":usage.get("prompt_tokens", ""),"output_tokens":usage.get("completion_tokens", ""),"error":""}
        except urllib.error.HTTPError as e:
            err="HTTP %d: %s"%(e.code,e.read().decode(errors="replace")[:400])
            if e.code in (401,403): return {"status":"error","error":err}
            if e.code != 429 and e.code < 500: return {"status":"error","error":err}
        except Exception as e: err="%s: %s"%(type(e).__name__,str(e)[:300])
        if attempt<4: time.sleep(2*(2**attempt)+random.random())
    return {"status":"error","error":err}

ap=argparse.ArgumentParser(); ap.add_argument("--providers",default="Qwen-DashScope,DeepSeek-Official"); ap.add_argument("--limit",type=int,default=0); args=ap.parse_args()
wanted=[x.strip() for x in args.providers.split(",") if x.strip()]
for x in wanted:
    if x not in PROVIDERS: raise SystemExit("Unknown provider: "+x)
with INPUT.open(encoding="utf-8-sig",newline="") as f: prompts=list(csv.DictReader(f))
if args.limit: prompts=prompts[:args.limit]
history=[]
if HISTORY.exists():
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        if line.strip(): history.append(json.loads(line))
latest={(r["sample_id"],r["provider"]):r for r in history}
started=now()
for name in wanted:
    p=PROVIDERS[name]; key=os.environ.get(p["env"],"")
    if not key:
        print("SKIP %s: missing %s"%(name,p["env"])); continue
    for i,row in enumerate(prompts,1):
        pair=(row["sample_id"],name)
        if latest.get(pair,{}).get("status")=="ok": continue
        result=call(p,key,row["prompt"])
        rec={**row,"record_id":row["sample_id"]+"|"+p["model"],"provider":name,"endpoint":p["endpoint"],"requested_model":p["model"],"temperature":0,"max_tokens":256,"collected_at_utc":now(),**result}
        with HISTORY.open("a",encoding="utf-8") as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
        history.append(rec); latest[pair]=rec
        print("%s %d/%d %s %s"%(name,i,len(prompts),row["sample_id"],result["status"])); time.sleep(.3)
rows=sorted(latest.values(),key=lambda r:(r["sample_id"],r["provider"]))
fields=[]
for r in rows:
    for k in r:
        if k not in fields: fields.append(k)
with OUTPUT.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
meta={"started_at_utc":started,"finished_at_utc":now(),"prompt_rows":len(prompts),"response_rows":len(rows),"ok":sum(r.get("status")=="ok" for r in rows),"errors":sum(r.get("status")!="ok" for r in rows),"providers":wanted,"system_prompt":SYSTEM,"temperature":0,"max_tokens":256}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(meta,ensure_ascii=False,indent=2))

