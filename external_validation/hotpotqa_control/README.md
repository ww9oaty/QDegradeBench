# HotpotQA evidence-degradation control

This experiment reduces construction and annotation subjectivity by deriving
critical-information removal from HotpotQA's official sentence-level
`supporting_facts` annotations.

## Fixed design

- Source: HotpotQA distractor validation split.
- Seed: `20261009`.
- Sample: 32 bridge questions with non-boolean answers.
- Selection requires at least two gold supporting facts and exactly one gold
  supporting sentence containing the normalized answer. The normalized answer
  may not occur in the question or any non-supporting context sentence.
- L2 is also rejected when a remaining title or sentence contains a lexical
  near-alias of the gold answer (token F1 at least 0.80).
- L0: original context, including distractors.
- L1: gold supporting sentences only.
- L2: gold supporting sentences except the answer-bearing sentence.
- L3: no evidence sentence.
- Intended answerability: A, A, P, U.
- Prompt output is fixed JSON with `status`, `answer`, and `reason`.

The construction is deterministic. The script records every exclusion count,
selected source ID, supporting-fact coordinate, and removed sentence.

## Input

Place the official file `hotpot_dev_distractor_v1.json` in this directory. The
official SHA256 listed by the HotpotQA dataset builder is:

`4e9ecb5c8d3b719f624d66b60f8d56bf227f03914f5f0753d6fa1b359d7104ea`

The Hugging Face Parquet mirror is also supported when `pyarrow` is available.
Chinese download instructions and checksums are in
`DOWNLOAD_INSTRUCTIONS_CN.md`.

## Commands

```text
python build_hotpotqa_control.py
python run_hotpotqa_control.py --providers Qwen-DashScope,DeepSeek-Official
python score_hotpotqa_control.py
```

API keys are read only from `DASHSCOPE_API_KEY` and `DEEPSEEK_API_KEY`.

## Formal run and audit files

- `hotpotqa_formal_deepseek_responses.csv` and `.jsonl`: the clean formal run,
  exactly 128 successful DeepSeek responses.
- `hotpotqa_api_errors.csv`: a separated Qwen permission-test error; it is not
  part of scoring.
- `hotpotqa_scored_responses.csv`: row-level automatic outcomes.
- `hotpotqa_metrics.json`: full 32-chain metrics and the declared 30-chain
  post-collection construct sensitivity.
- `HOTPOTQA_FORMAL_RUN_REPORT.md`: source checksum, run settings, results,
  interpretation limits, and remaining verification.
- `POST_COLLECTION_CONSTRUCT_AUDIT.md`: why HP09 and HP23 remain in the primary
  result but are excluded from the sensitivity analysis.
- `hotpotqa_human_audit.csv`: 10% stratified sample plus every automatic
  failure; human decision columns remain blank until a reviewer confirms them.
- `hotpotqa_human_audit_cn.md`: Chinese review aid with a proposed judgment and
  explicit basis for each of the 40 audit rows.

The original append-only `hotpotqa_responses.jsonl` is retained as local run
history. Public releases should use the clean formal response files and retain
the separated error log for transparency.

