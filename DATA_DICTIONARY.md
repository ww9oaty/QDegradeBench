# Data dictionary

## prompts.csv

- `sample_id`: prompt identifier, combining the base task and degradation level.
- `base_task_id`: identifier shared by the four versions of one task.
- `task_type`: Numerical Reasoning, Code Diagnosis, Constrained Generation, or Decision and Planning.
- `level`: degradation level L0-L3.
- `answerability`: A, P, or U.
- `prompt`: Chinese prompt text.

## responses.csv

- `record_id`: unique response identifier.
- `sample_id`: link to `prompts.csv`.
- `base_task_id`: matched-chain identifier.
- `task_type`: task category.
- `level`: L0-L3.
- `answerability`: A, P, or U.
- `provider`: endpoint family used in the experiment.
- `model`: recorded endpoint/model identifier.
- `prompt`: exact prompt supplied to the endpoint.
- `response`: returned model text.
- `final_label`: human-confirmed response-behavior label.
- `max_tokens`: configured maximum output length.
- `finish_reason`: API termination metadata when available.
- `output_tokens`: recorded output-token count.

## double_review_sample.csv

- `primary_human_label`: first annotator's label before consensus discussion.
- `second_human_label`: second annotator's independent label.
- `initial_agreement`: source agreement flag.
- `final_label`: label used after the review process.

The remaining identifier and task columns match `responses.csv`.

## external_validation/e2e_annotation_sheet_human_reviewed.csv

The response and collection fields match `external_validation/e2e_model_responses.csv`. The additional review fields are:

- `final_label`: human-confirmed CA/PA/CQ/AI/UA/IR behavior label.
- `review_note`: concise evidence note for the final decision.
- `unsupported_required_value`: `yes` when the response supplies at least one omitted required L2 attribute value without support; otherwise `no` (`not_applicable` outside the audited condition).
- `unsupported_extra_claim`: whether the response adds another unsupported factual claim.
- `complete_missing_acknowledgment`: `yes` when both omitted L2 fields are explicitly identified as missing, `partial` when exactly one is identified, and `no` when neither is identified (`not_applicable` outside L2).
- `factual_instruction_compliance`: `yes` when the response follows the complete factual and missing-information instruction; otherwise `no`.

All three reported L2 rates use responses as the unit and 48 L2 responses as the overall denominator. The unsupported-required-value rate is not an attribute-level error rate.
