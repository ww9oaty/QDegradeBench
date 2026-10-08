# Public English External Validation

This directory contains the completed factual-framing control built from the public E2E NLG Challenge restaurant data.

## Design

- 24 source records sampled with seed 20261001.
- Four matched degradation levels per record, giving 96 English prompts.
- L0 and L1 provide all eight required attributes.
- L2 removes two required attribute values.
- L3 provides no restaurant-specific attribute values.
- Two deployed endpoints produced one response per prompt, giving 192 responses.

The prompts explicitly frame the task as factual data-to-text generation, prohibit invented values and factual claims, and instruct the model to identify or request missing required values.

## Files

- `e2e_qdegrade_24x4.csv`: the 96 factual-framing prompts and degradation metadata.
- `e2e_model_responses.csv`: the 192 collected endpoint responses and API metadata.
- `e2e_annotation_sheet_human_reviewed.csv`: final human-confirmed behavior labels and review notes.
- `e2e_metrics_human_reviewed.json`: complete overall and endpoint-level metrics.
- `compute_e2e_metrics.py`: reproduces label counts, ARR, UAR, IDU, and CFO.
- `e2e_run_metadata.json` and `e2e_run_report.md`: collection settings and integrity checks.
- `e2e_testset_w_refs.csv`: retained public-source records and references for provenance.
- `E2E_SOURCE_AND_LICENSE.md`: source attribution and license notes.

## Reproduction

From this directory, run:

```text
python compute_e2e_metrics.py e2e_annotation_sheet_human_reviewed.csv
```

The expected analysis status is `complete`, with 192 labeled rows. Overall ARR is 100.0% at L0, 100.0% at L1, 87.5% at L2, and 100.0% at L3. The six unsupported answers all occur at L2.

## Interpretation limits

This is an exploratory transfer check using 24 chains from one structured restaurant domain. The 24 L3 rows repeat one unique prompt, so they are repeated endpoint observations rather than 24 independent L3 items. The factual-framing prompt combines several instructions and does not isolate the effect of any single instruction component.
