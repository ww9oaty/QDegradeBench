# E2E external validation run report

- Generated: 2026-10-08T04:00:27.834495+00:00
- Prompt input: `e2e_qdegrade_24x4.csv` (96 prompts: 24 tasks x L0-L3)
- Expected responses: 192 (2 models x 96)

## Providers run in this session

| Provider | Requested model | Endpoint |
|---|---|---|
| DeepSeek-Official | deepseek-v4-pro | https://api.deepseek.com/chat/completions |

## Integrity summary

| Check | Value |
|---|---|
| Expected total | 192 |
| Actual records | 192 |
| OK | 192 |
| Failed | 0 |
| OK but empty response | 0 |

### Per model

| Model | Total | OK | Failed |
|---|---|---|---|
| deepseek-v4-pro | 96 | 96 | 0 |
| qwen3.7-plus | 96 | 96 | 0 |

### OK counts per level per model (target 24 each)

| Level | deepseek-v4-pro | qwen3.7-plus |
|---|---|---|
| L0 | 24 | 24 |
| L1 | 24 | 24 |
| L2 | 24 | 24 |
| L3 | 24 | 24 |

## Files

- Responses JSONL: `e2e_model_responses.jsonl` (append-only history)
- Responses CSV: `e2e_model_responses.csv` (latest record per sample/provider)
- Failures CSV: `e2e_failed_records.csv` (0 rows)
- Metadata JSON: `e2e_run_metadata.json`
- Report: `e2e_run_report.md`

## Notes

- All outputs are UTF-8 encoded; API keys are never stored in any output.
- No behavior labels are applied in this stage; responses are collected only.
- Re-run the same command to resume: completed OK records are skipped,
  failed records are retried.
