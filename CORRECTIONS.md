# v1.0.1 data-alignment correction — 2026-10-09

The v1.0.0 annotation export incorrectly joined factual-control labels to earlier-condition prompts and responses sharing the same record IDs. Its prompt CSV also described the earlier condition. Do not use v1.0.0 for prompt-response-label analyses.

v1.0.1 restores the actual factual-control prompts and responses underlying the human review, corrects the blank annotation sheet and prompt builder, and retains the confirmed labels. All 192 reviewed prompt-response pairs match the collected factual-control records exactly. Label-derived metrics are unchanged: L2 PA/CA/UA = 34/8/6 and ARR = 87.5%. This numerical agreement alone was insufficient to validate v1.0.0.

Review used AI-assisted Chinese translations and label suggestions followed by human confirmation; it is not an independent second review. The original v1.0.0 tag is retained for transparency.
