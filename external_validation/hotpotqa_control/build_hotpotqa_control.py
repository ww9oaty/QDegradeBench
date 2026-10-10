"""Build 32 deterministic HotpotQA evidence-degradation chains."""
import csv, hashlib, json, random, re, string
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JSON_INPUT = ROOT / "hotpot_dev_distractor_v1.json"
PARQUET_INPUT = ROOT / "hotpot_distractor_validation.parquet"
OUT_CSV = ROOT / "hotpotqa_32x4.csv"
OUT_JSONL = ROOT / "hotpotqa_32x4.jsonl"
MANIFEST = ROOT / "hotpotqa_build_manifest.json"
SEED = 20261009
TARGET = 32
EXPECTED_JSON_SHA256 = "4e9ecb5c8d3b719f624d66b60f8d56bf227f03914f5f0753d6fa1b359d7104ea"
EXPECTED_PARQUET_SHA256 = "c20b638ca82b21d04fe12e14ff417ad05153d4d215a65de54497fca4e972f7c6"
MANUAL_CONSTRUCT_EXCLUSIONS = {
    "5a7e7c725542991319bc94be": (
        "Question asks when a race was won, but the official supporting facts only "
        "state the horse's foaling date and the gold answer is the foaling date."
    )
}

def norm(s):
    s = str(s).lower()
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = "".join(ch for ch in s if ch not in string.punctuation)
    return " ".join(s.split())

def contains_answer(text, answer_norm):
    """Token-bounded normalized match; avoids e.g. 'us' matching 'music'."""
    return (" " + answer_norm + " ") in (" " + norm(text) + " ")

def near_answer_in_text(text, answer_norm, threshold=0.80):
    """Detect lexical aliases left after deletion, such as a name without a suffix."""
    target=answer_norm.split(); tokens=norm(text).split()
    if not target or not tokens: return False
    for width in range(max(1,len(target)-1),min(len(tokens),len(target)+2)+1):
        for start in range(len(tokens)-width+1):
            candidate=tokens[start:start+width]
            overlap=sum((Counter(candidate)&Counter(target)).values())
            if not overlap: continue
            precision=overlap/len(candidate); recall=overlap/len(target)
            f1=2*precision*recall/(precision+recall)
            if f1>=threshold: return True
    # Conservative entity-token check. This catches shortened names, singular/
    # plural variants, and light inflections that would still reveal the answer.
    stop={"the","and","for","from","with","into","that","this","was","were",
          "company","team","film","song","game","city","state","university",
          "club","band","actor","actress","writer","author","form","role",
          "year","years","feet","limited","corporation"}
    def light_stem(token):
        if len(token)>5 and token.endswith("ies"): return token[:-3]+"y"
        if len(token)>5 and token.endswith("ing"): return token[:-3]
        if len(token)>4 and token.endswith("ed"): return token[:-2]
        if len(token)>4 and token.endswith("s"): return token[:-1]
        return token
    answer_terms={light_stem(x) for x in target if len(x)>=4 and x not in stop}
    text_terms={light_stem(x) for x in tokens if len(x)>=4 and x not in stop}
    if answer_terms & text_terms: return True
    return False

def load_rows():
    if JSON_INPUT.exists():
        raw = JSON_INPUT.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        rows = json.loads(raw.decode("utf-8"))
        return rows, {"path": str(JSON_INPUT), "format": "official_json", "sha256": sha,
                      "matches_official_sha256": sha == EXPECTED_JSON_SHA256}
    if PARQUET_INPUT.exists():
        try:
            import pandas as pd
            rows = pd.read_parquet(PARQUET_INPUT).to_dict("records")
        except Exception as e:
            raise SystemExit("Parquet input requires pandas plus pyarrow: %s" % e)
        raw = PARQUET_INPUT.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        return rows, {"path": str(PARQUET_INPUT), "format": "hf_parquet_mirror",
                      "sha256": sha,
                      "matches_published_sha256": sha == EXPECTED_PARQUET_SHA256}
    raise SystemExit("Missing HotpotQA input. See README.md.")

def unpack_context(row):
    c = row["context"]
    if isinstance(c, dict):
        return list(zip(list(c["title"]), list(c["sentences"])))
    return [(x[0], x[1]) for x in c]

def unpack_support(row):
    s = row["supporting_facts"]
    if isinstance(s, dict):
        return list(zip(list(s["title"]), [int(x) for x in s["sent_id"]]))
    return [(x[0], int(x[1])) for x in s]

def render_context(items):
    if not items:
        return "[No evidence is provided.]"
    return "\n".join("[%s] %s" % (title, sentence.strip()) for title, sentence in items)

def prompt(question, items):
    return (
        "Treat this as evidence-bounded question answering. Use only the evidence "
        "shown below and do not use outside knowledge. If the evidence is sufficient, "
        "answer the question. If any necessary evidence is missing, set status to "
        "insufficient and leave answer empty. Return exactly one JSON object with keys "
        "status, answer, and reason. status must be answer or insufficient.\n\n"
        "Question: %s\n\nEvidence:\n%s" % (question.strip(), render_context(items))
    )

def normalize_row(row):
    return {
        "id": str(row.get("_id", row.get("id", ""))),
        "question": str(row["question"]), "answer": str(row["answer"]),
        "type": str(row.get("type", "")), "level": str(row.get("level", "")),
        "context": unpack_context(row), "support": unpack_support(row),
    }

rows, source = load_rows()
counts = Counter(total_source=len(rows))
eligible = []
for raw in rows:
    r = normalize_row(raw)
    if r["type"] != "bridge": counts["exclude_not_bridge"] += 1; continue
    a = norm(r["answer"])
    if a in {"yes", "no"} or len(a) < 3: counts["exclude_answer_type"] += 1; continue
    if contains_answer(r["question"], a): counts["exclude_answer_in_question"] += 1; continue
    if contains_answer(prompt(r["question"], []), a):
        counts["exclude_answer_in_fixed_template"] += 1; continue
    lookup = {title: sentences for title, sentences in r["context"]}
    support = []
    invalid = False
    for title, idx in r["support"]:
        if title not in lookup or idx < 0 or idx >= len(lookup[title]): invalid = True; break
        support.append((title, idx, str(lookup[title][idx])))
    if invalid or len(support) < 2: counts["exclude_invalid_or_short_support"] += 1; continue
    answer_support = [x for x in support if contains_answer(x[2], a)]
    if len(answer_support) != 1: counts["exclude_nonunique_answer_support"] += 1; continue
    support_coords = {(t, i) for t, i, _ in support}
    non_support = [(t, i, str(s)) for t, ss in r["context"] for i, s in enumerate(ss)
                   if (t, i) not in support_coords]
    if any(contains_answer(s, a) for _, _, s in non_support): counts["exclude_answer_in_nonsupport"] += 1; continue
    removed = answer_support[0]
    remaining = [x for x in support if (x[0], x[1]) != (removed[0], removed[1])]
    if (not remaining or any(contains_answer(x[2], a) for x in remaining)
            or any(contains_answer(x[0], a) for x in remaining)):
        counts["exclude_invalid_l2"] += 1; continue
    remaining_rendered=render_context([(t,s) for t,_,s in remaining])
    if near_answer_in_text(remaining_rendered,a):
        counts["exclude_near_answer_alias_in_l2"] += 1; continue
    full = [(t, str(s)) for t, ss in r["context"] for s in ss]
    if len(prompt(r["question"], full)) > 24000: counts["exclude_prompt_too_long"] += 1; continue
    r.update(answer_norm=a, support_records=support, removed=removed, remaining=remaining, full=full)
    eligible.append(r)

counts["eligible"] = len(eligible)
if len(eligible) < TARGET:
    raise SystemExit("Only %d eligible rows; need %d" % (len(eligible), TARGET))
rng = random.Random(SEED)
rng.shuffle(eligible)
counts["exclude_manual_construct_invalid"] = sum(
    r["id"] in MANUAL_CONSTRUCT_EXCLUSIONS for r in eligible
)
eligible = [r for r in eligible if r["id"] not in MANUAL_CONSTRUCT_EXCLUSIONS]
selected = eligible[:TARGET]

out = []
for n, r in enumerate(selected, 1):
    base = "HP%02d" % n
    levels = [
        ("L0", "A", r["full"]),
        ("L1", "A", [(t, s) for t, _, s in r["support_records"]]),
        ("L2", "P", [(t, s) for t, _, s in r["remaining"]]),
        ("L3", "U", []),
    ]
    for level, answerability, items in levels:
        out.append({
            "sample_id": base + "_" + level, "base_task_id": base,
            "level": level, "answerability": answerability,
            "source_id": r["id"], "source_type": r["type"],
            "source_level": r["level"], "question": r["question"],
            "gold_answer": r["answer"], "gold_answer_norm": r["answer_norm"],
            "supporting_fact_count": len(r["support_records"]),
            "removed_title": r["removed"][0], "removed_sent_id": r["removed"][1],
            "removed_sentence": r["removed"][2],
            "visible_evidence_count": len(items), "prompt": prompt(r["question"], items),
        })

assert len(out) == TARGET * 4
for base in {r["base_task_id"] for r in out}:
    g = [r for r in out if r["base_task_id"] == base]
    assert [r["level"] for r in g] == ["L0", "L1", "L2", "L3"]
    assert len({r["question"] for r in g}) == 1
    assert not contains_answer(g[0]["question"], g[0]["gold_answer_norm"])
    assert contains_answer(g[0]["prompt"], g[0]["gold_answer_norm"])
    assert contains_answer(g[1]["prompt"], g[0]["gold_answer_norm"])
    assert not contains_answer(g[2]["prompt"], g[0]["gold_answer_norm"])
    assert not contains_answer(g[3]["prompt"], g[0]["gold_answer_norm"])

fields = list(out[0])
with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
with OUT_JSONL.open("w", encoding="utf-8") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")

manifest = {"source": source, "seed": SEED, "target_chains": TARGET,
            "source_counts": dict(counts), "output_rows": len(out),
            "selected_source_ids": [r["id"] for r in selected],
            "manual_construct_exclusions": MANUAL_CONSTRUCT_EXCLUSIONS,
            "selection_independent_of_model_outputs": True}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(manifest, ensure_ascii=False, indent=2))

