# QDegradeBench Public Research Artifact

QDegradeBench evaluates model behavior as task-critical information is progressively removed from otherwise matched prompts.

Public repository: https://github.com/ww9oaty/QDegradeBench

## Contents

- `prompts.csv`: 128 Chinese prompts from 32 base tasks and four degradation levels.
- `responses.csv`: 512 responses from four API endpoints with final human-confirmed labels.
- `double_review_sample.csv`: the stratified sample of 128 responses reviewed independently by two human annotators.
- `QDegradeBench_public_data.xlsx`: the same public data in workbook form.
- `LABELS.md`: response labels and answerability categories.
- `DATA_DICTIONARY.md`: field definitions.
- `analysis/reproduce_metrics.py`: reproduces the main counts, ARR, UAR, IDU, CFO distribution, agreement, and Cohen's kappa.
- `external_validation/`: two public English controls: the 24-chain E2E transfer study and the 32-chain HotpotQA evidence-deletion study.

## Data exclusions

AI-generated preliminary labels are not included. Reviewer names, internal notes, adjudication comments, API credentials, and private service configuration are also excluded. The released `final_label` field is the human-confirmed label used in the paper's analysis.

## Reproduction

From the package root, run:

```text
python analysis/reproduce_metrics.py
```

The script uses only the Python standard library.

To reproduce the public English external-validation metrics, run:

```text
python external_validation/compute_e2e_metrics.py external_validation/e2e_annotation_sheet_human_reviewed.csv
```

The HotpotQA control is in `external_validation/hotpotqa_control/`. Its clean
formal files contain 128 successful DeepSeek responses. The directory includes
the deterministic constructor, source checksum, strict automatic scores,
40-response human semantic audit, and a disclosed 30-chain construct
sensitivity that excludes two residual-cue trajectories. See its `README.md`
and `HOTPOTQA_FORMAL_RUN_REPORT.md` for commands and interpretation limits.

## Dataset structure

Each base task has four matched prompts:

- L0: complete prompt with redundant information.
- L1: redundant information removed; the task remains answerable.
- L2: the first removal of critical information; the prompt is partially answerable.
- L3: maximum critical-information removal; the prompt is generally unanswerable, with one documented partially answerable case.

Each prompt was sent once to each of four API endpoints. The unit of a degradation trajectory is one API endpoint paired with one base task across L0-L3.

## License

This artifact is released under CC BY 4.0. See `LICENSE.txt`.

## Archived versions

Version `v1.0.3` adds the HotpotQA public-data control and its completed
40-response single-reviewer semantic audit. Tag `v1.0.2` contains the corrected
E2E factual-control data plus its human-confirmed L2 structured audit. The
original `v1.0.0` has a prompt-response-label alignment error; see
`CORRECTIONS.md`. Version `v1.0.1` corrects that alignment but predates the
structured audit fields.

