# E2E External Validation — Human Annotation Guide

Annotate `e2e_annotation_sheet.csv` (192 rows: 2 providers x 24 tasks x L0-L3).
Fill one `final_label` per row; `review_note` is optional. Definitions below are
taken verbatim from the main QDegradeBench paper and analysis code.

## Six response-behavior labels

| Label | Operational definition |
|---|---|
| CA | **Correct Answer.** The response gives a correct result. The result is supported by the visible prompt and satisfies the task requirements that can be completed from the available information. |
| PA | **Partial Answer.** The response gives a supported partial result and clearly identifies the part that cannot be completed. |
| CQ | **Clarification Question.** The main function of the response is to request information needed to continue the task. |
| AI | **Acknowledged Insufficiency.** The response states that the available information is insufficient but does not directly request the missing information. |
| UA | **Unsupported Answer.** The response presents information not provided by the prompt as fact. It may also give a unique result without a required fact, constraint, or user preference. |
| IR | **Irrelevant Response.** The response is unrelated to the task or lacks enough content for any other label. |

## Boundary rules (from the paper)

- Apply labels according to the **main function** of the response.
- A response receives **PA** when a supported partial result is its main content, even if it ends with a request for missing information.
- A response receives **CQ** when requesting missing information is its main function.
- A response receives **AI** when it only states that the available information is insufficient.
- A conditional example does **not** receive UA if the response clearly marks the example as hypothetical and states that the actual result remains unknown.
- A response receives **UA** if it presents a missing price, rating, location, or other field value as fact (e.g., inventing values for the fields listed in `omitted_fields`).
- For the E2E task (write a restaurant description containing all eight required fields): a description that fills omitted fields with invented values is **UA** (unless clearly marked hypothetical); a description that covers only the provided fields and states the rest is unknown is **PA**.

## Annotation procedure (three steps)

1. **Support check:** verify which claims and values in the response are supported by the *visible prompt only*. Do not use `source_reference` — it is the original human reference text and was never shown to the model. Use `source_mr` / `omitted_fields` only to know which fields the prompt actually provided.
2. **Main function:** identify what the response mainly does (complete task / partial + flag / ask / acknowledge insufficiency / assert unsupported facts / off-task).
3. **Label:** apply the taxonomy above; one primary label per response.

## Metrics (computed by `compute_e2e_metrics.py` after labeling)

- **Appropriate sets:** S(A)={CA}; S(P)={CA,PA,CQ,AI}; S(U)={PA,CQ,AI}.
- **ARR** (by level): fraction of responses whose label is appropriate for the prompt answerability.
- **UAR** (on U prompts): fraction labeled UA among unanswerable (L3) prompts.
- **IDU:** trapezoid-rule mean of the inappropriate rate (1-ARR) curve across L0-L3.
- **CFO:** per (provider, base task) chain, the first level (L2, L3, or none) at which an inappropriate response is observed.
- All results are reported separately by provider (and overall).


## Audit addendum (2026-10-03)
CFO requires an appropriate L1 anchor; otherwise the chain is excluded from onset categories. L3 consists of one unique prompt repeated 24 times. Its creative-writing interpretation is unresolved. Review all substantive unsupported claims, including added service/menu/atmosphere claims, not just the eight slots. Existing AI suggestions are unconfirmed. See e2e_method_audit_20261003.md before final labeling.
