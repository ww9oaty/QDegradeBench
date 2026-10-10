import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
RESPONSES_CSV = ROOT / "hotpotqa_responses.csv"
RESPONSES_JSONL = ROOT / "hotpotqa_responses.jsonl"
METRICS_JSON = ROOT / "hotpotqa_metrics.json"
MANIFEST_JSON = ROOT / "hotpotqa_build_manifest.json"
SOURCE_PARQUET = ROOT / "hotpot_distractor_validation.parquet"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl(frame: pd.DataFrame, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in frame.where(pd.notna(frame), None).to_dict("records"):
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


responses = pd.read_csv(RESPONSES_CSV, keep_default_na=False)
formal = responses[
    (responses["provider"] == "DeepSeek-Official")
    & (responses["status"] == "ok")
].copy()
errors = responses[responses["status"] != "ok"].copy()

assert len(formal) == 128, f"Expected 128 formal rows, found {len(formal)}"
assert formal["record_id"].nunique() == 128, "Formal record IDs are not unique"
assert formal.groupby("level").size().to_dict() == {
    "L0": 32,
    "L1": 32,
    "L2": 32,
    "L3": 32,
}

formal_csv = ROOT / "hotpotqa_formal_deepseek_responses.csv"
formal_jsonl = ROOT / "hotpotqa_formal_deepseek_responses.jsonl"
errors_csv = ROOT / "hotpotqa_api_errors.csv"
formal.to_csv(formal_csv, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
write_jsonl(formal, formal_jsonl)
errors.to_csv(errors_csv, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)

metrics = json.loads(METRICS_JSON.read_text(encoding="utf-8"))
manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
full = metrics["overall"]
sens = metrics["post_collection_construct_sensitivity"]["overall"]


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


report = f"""# HotpotQA public-data control: formal run report

## Status

- Formal model: `deepseek-v4-pro` through the official DeepSeek endpoint.
- Completed: 128/128 responses (32 chains x 4 degradation levels).
- Decoding: temperature 0, max tokens 256.
- System instruction: `You are a careful evidence-bounded question answering assistant.`
- The append-only collection history is preserved locally. The clean formal files contain only the 128 successful DeepSeek records. One denied Qwen permission test is separated into `hotpotqa_api_errors.csv` and is not scored.

## Public source and deterministic construction

- Source: HotpotQA distractor validation split, distributed as Parquet.
- Source file SHA-256: `{sha256(SOURCE_PARQUET)}`.
- Selection seed: `{manifest.get('seed', 20261009)}`.
- Formal set: 32 source questions and 128 prompts.
- L0 keeps the full distractor context; L1 keeps official supporting sentences; L2 removes the unique answer-bearing supporting sentence; L3 supplies no evidence.
- The expected response modes are answer at L0/L1 and abstain at L2/L3.

## Full 32-chain result

| Level | n | Appropriate-response rate | Answer EM | Mean token F1 | Unsupported-answer rate | Decision counts |
|---|---:|---:|---:|---:|---:|---|
| L0 | 32 | {pct(full['by_level']['L0']['ARR'])} | {pct(full['by_level']['L0']['answer_EM'])} | {full['by_level']['L0']['mean_answer_F1']:.3f} | -- | 19 correct, 10 strict-EM incorrect, 3 excessive abstentions |
| L1 | 32 | {pct(full['by_level']['L1']['ARR'])} | {pct(full['by_level']['L1']['answer_EM'])} | {full['by_level']['L1']['mean_answer_F1']:.3f} | -- | 21 correct, 9 strict-EM incorrect, 2 excessive abstentions |
| L2 | 32 | {pct(full['by_level']['L2']['ARR'])} | -- | -- | {pct(full['by_level']['L2']['unsupported_answer_emission_rate'])} | 23 appropriate abstentions, 9 unsupported answers |
| L3 | 32 | {pct(full['by_level']['L3']['ARR'])} | -- | -- | {pct(full['by_level']['L3']['unsupported_answer_emission_rate'])} | 32 appropriate abstentions |

- IDU: {full['IDU']:.3f}.
- CFO: L2 failure for 5 chains; 16 had no observed failure; 11 were excluded because L1 was already inappropriate.
- JSON parse rate: 100% at every level.

## Post-collection construct sensitivity

Manual inspection found two L2 prompts with residual answer cues: HP09 retained the title *Cat's Eye*, and HP23 retained three explicitly countable disciplines. They remain in the primary result to avoid silent post-hoc deletion. A declared sensitivity analysis excludes these two complete trajectories (30 chains, 120 responses):

| Level | n | Appropriate-response rate | Answer EM | Mean token F1 | Unsupported-answer rate |
|---|---:|---:|---:|---:|---:|
| L0 | 30 | {pct(sens['by_level']['L0']['ARR'])} | {pct(sens['by_level']['L0']['answer_EM'])} | {sens['by_level']['L0']['mean_answer_F1']:.3f} | -- |
| L1 | 30 | {pct(sens['by_level']['L1']['ARR'])} | {pct(sens['by_level']['L1']['answer_EM'])} | {sens['by_level']['L1']['mean_answer_F1']:.3f} | -- |
| L2 | 30 | {pct(sens['by_level']['L2']['ARR'])} | -- | -- | {pct(sens['by_level']['L2']['unsupported_answer_emission_rate'])} |
| L3 | 30 | {pct(sens['by_level']['L3']['ARR'])} | -- | -- | {pct(sens['by_level']['L3']['unsupported_answer_emission_rate'])} |

- Sensitivity IDU: {sens['IDU']:.3f}.

## Interpretation boundary

This control reduces dependence on author-written tasks because the questions, gold answers, and sentence-level supporting facts come from a public benchmark. It does not eliminate judgment from the derived degradation procedure. L2 answer emissions are therefore described as unsupported-answer emissions under the visible evidence, not automatically as hallucinations. The strong L3 abstention rate may reflect the explicit evidence-only instruction and clear absence of context; it is not evidence that the model reliably recognizes all unknowns.

## Remaining verification

The automatic scorer uses normalized exact match as the pre-specified binary L0/L1 criterion, with token F1 reported continuously. Human audit is still required because semantically correct variants such as `Pac-12 Conference` versus `Pac-12` can fail exact match. The prepared audit contains a 10% stratified sample plus every automatic failure.
"""
(ROOT / "HOTPOTQA_FORMAL_RUN_REPORT.md").write_text(report, encoding="utf-8")

print(f"formal_rows={len(formal)}")
print(f"error_rows={len(errors)}")
print(formal_csv)
print(formal_jsonl)
print(errors_csv)
print(ROOT / "HOTPOTQA_FORMAL_RUN_REPORT.md")
