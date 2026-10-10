# HotpotQA public-data control: formal run report

## Status

- Formal model: `deepseek-v4-pro` through the official DeepSeek endpoint.
- Completed: 128/128 responses (32 chains x 4 degradation levels).
- Decoding: temperature 0, max tokens 256.
- System instruction: `You are a careful evidence-bounded question answering assistant.`
- The append-only collection history is preserved locally. The clean formal files contain only the 128 successful DeepSeek records. One denied Qwen permission test is separated into `hotpotqa_api_errors.csv` and is not scored.

## Public source and deterministic construction

- Source: HotpotQA distractor validation split, distributed as Parquet.
- Source file SHA-256: `c20b638ca82b21d04fe12e14ff417ad05153d4d215a65de54497fca4e972f7c6`.
- Selection seed: `20261009`.
- Formal set: 32 source questions and 128 prompts.
- L0 keeps the full distractor context; L1 keeps official supporting sentences; L2 removes the unique answer-bearing supporting sentence; L3 supplies no evidence.
- The expected response modes are answer at L0/L1 and abstain at L2/L3.

## Full 32-chain result

| Level | n | Appropriate-response rate | Answer EM | Mean token F1 | Unsupported-answer rate | Decision counts |
|---|---:|---:|---:|---:|---:|---|
| L0 | 32 | 59.4% | 59.4% | 0.794 | -- | 19 correct, 10 strict-EM incorrect, 3 excessive abstentions |
| L1 | 32 | 65.6% | 65.6% | 0.819 | -- | 21 correct, 9 strict-EM incorrect, 2 excessive abstentions |
| L2 | 32 | 71.9% | -- | -- | 28.1% | 23 appropriate abstentions, 9 unsupported answers |
| L3 | 32 | 100.0% | -- | -- | 0.0% | 32 appropriate abstentions |

- IDU: 0.276.
- CFO: L2 failure for 5 chains; 16 had no observed failure; 11 were excluded because L1 was already inappropriate.
- JSON parse rate: 100% at every level.

## Post-collection construct sensitivity

Manual inspection found two L2 prompts with residual answer cues: HP09 retained the title *Cat's Eye*, and HP23 retained three explicitly countable disciplines. They remain in the primary result to avoid silent post-hoc deletion. A declared sensitivity analysis excludes these two complete trajectories (30 chains, 120 responses):

| Level | n | Appropriate-response rate | Answer EM | Mean token F1 | Unsupported-answer rate |
|---|---:|---:|---:|---:|---:|
| L0 | 30 | 60.0% | 60.0% | 0.791 | -- |
| L1 | 30 | 66.7% | 66.7% | 0.841 | -- |
| L2 | 30 | 76.7% | -- | -- | 23.3% |
| L3 | 30 | 100.0% | -- | -- | 0.0% |

- Sensitivity IDU: 0.256.

## Interpretation boundary

This control reduces dependence on author-written tasks because the questions, gold answers, and sentence-level supporting facts come from a public benchmark. It does not eliminate judgment from the derived degradation procedure. L2 answer emissions are therefore described as unsupported-answer emissions under the visible evidence, not automatically as hallucinations. The strong L3 abstention rate may reflect the explicit evidence-only instruction and clear absence of context; it is not evidence that the model reliably recognizes all unknowns.

## Human semantic audit

The automatic scorer uses normalized exact match as the pre-specified binary L0/L1 criterion, with token F1 reported continuously. One human reviewer checked 40 of 128 responses: a stratified sample plus every automatic failure. The audit changed 21 automatic dispositions, including semantically correct variants such as `Pac-12 Conference` versus `Pac-12` and two residual-cue cases reclassified as construct leakage. In the declared 30-chain sensitivity, human-adjudicated ARR was 90.0% at L0, 93.3% at L1, 76.7% at L2, and 100.0% at L3; seven L2 responses emitted unsupported answers. The review was not independent or blinded, and the original automatic outcomes remain available.
