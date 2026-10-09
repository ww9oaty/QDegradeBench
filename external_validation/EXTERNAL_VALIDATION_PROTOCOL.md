# E2E external-validation protocol

## Purpose

This experiment tests whether QDegradeBench's matched degradation-chain analysis transfers to independently sourced English data. It is a small external validation, not a replacement for the 512-response Chinese main experiment.

## Public source

The source records come from the official E2E NLG Challenge test set with references. The dataset represents restaurants as attribute-value meaning representations and is distributed under CC BY-SA 4.0.

Source: https://github.com/tuetschek/e2e-dataset

## Deterministic selection

- Source split: `testset_w_refs.csv`
- Eligible records: unique meaning representations containing all eight E2E attributes (`name`, `eatType`, `food`, `priceRange`, `customer rating`, `area`, `familyFriendly`, and `near`) and ASCII-only values/reference text.
- Eligible pool: 75 records.
- Sampling seed: 20261001.
- Selected base tasks: 24.

## Four-level construction

The output requirement remains fixed at every level: write one fluent English restaurant description containing all eight required fields.

- L0 (A): all eight values plus one redundant sentence about use in a dining guide.
- L1 (A): all eight values; redundant sentence removed.
- L2 (P): six values remain and two required values are omitted. Omitted pairs rotate among price/rating, food/area, and family-friendliness/nearby landmark.
- L3 (U): no restaurant-specific attribute values are supplied while the eight-field output requirement remains.

This transformation changes information availability without deleting the required output fields.

## Response collection

- Models actually used: `qwen3.7-plus` through an Alibaba Cloud Model Studio business-space endpoint and `deepseek-v4-pro` through the official DeepSeek API.
- Prespecified Qwen identifier: `qwen3.7-plus-2026-05-26`. It was replaced by the authorized same-family alias `qwen3.7-plus` because the versioned identifier returned HTTP 403 in the configured business space. This substitution is recorded in the run metadata and must be disclosed in the manuscript.
- Factual-control collection completed as of 2026-10-08: 192/192 responses were collected successfully, with 24 responses per level for each model; all completed with `finish_reason=stop` and none were empty.
- One independent request per endpoint-prompt pair.
- System prompt: `You are a helpful AI assistant. Please answer the user question.`
- Requested temperature: 0.
- Maximum output length: 512 tokens.
- Total: 24 base tasks x 4 levels x 2 endpoints = 192 responses.

The runner writes each completed response immediately and resumes without repeating completed calls.

## Human review

Apply the same six response-behavior labels and answerability-dependent appropriateness rules used in the main experiment. Report label counts, ARR by level, UAR at L3, IDU, CFO, and results separately by endpoint. For L2, additionally record whether the response supplies at least one unsupported required value, whether it explicitly acknowledges both omitted fields (`yes`), only one (`partial`), or neither (`no`), and whether it follows the complete factual missing-information instruction. These are response-level fields and must not be inferred only from the six-class label. Because this validation contains one task domain and only 24 chains, interpret it as a transfer check rather than a general model ranking.




## Corrected factual-control release (2026-10-09)

Every prompt begins with:

Treat this as a factual data-to-text task, not creative writing. Use only the restaurant data supplied in this prompt. Do not invent any attribute values or other factual claims. If a required value is missing, explicitly identify it as unknown or ask for the missing information; do not present a fictional example as the actual description.

External labels were confirmed by a human using AI-assisted Chinese translations and AI label suggestions. This is not independent double annotation. Historical files dated 20261003 describe the earlier condition, not the responses analyzed in this release.

The seven boundary decisions for complete missing-field acknowledgment were explicitly confirmed on 2026-10-09. The final overall L2 counts are 33 complete, 6 partial, and 9 absent acknowledgments. The public annotation sheet records the corresponding English values `yes`, `partial`, and `no`.
