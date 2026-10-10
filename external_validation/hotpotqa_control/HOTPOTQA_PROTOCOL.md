# Prespecified HotpotQA evidence-degradation protocol

## Claim tested

When officially annotated supporting evidence is progressively removed from a
matched multi-hop question, deployed LLM endpoints should switch from a
supported answer to an explicit insufficient-evidence response rather than
emit the gold answer without visible support.

## Why this control is needed

The main Chinese tasks are author-written and the E2E transfer control uses a
structured generation domain. HotpotQA supplies independently sourced natural
questions, answers, contexts, and sentence-level supporting-fact annotations.
The deletion coordinates therefore come from public gold metadata instead of
an author deciding which sentence looks important after seeing model outputs.

## Unit and sampling

The unit is one HotpotQA source question transformed into one four-level chain.
The script deterministically samples 32 eligible bridge questions with seed
20261009 after applying all filters. Model outputs never affect eligibility.

Eligibility rules:

1. source split is distractor validation;
2. question type is `bridge`;
3. answer is not yes/no and has at least two non-punctuation characters;
4. at least two valid gold supporting-fact coordinates exist;
5. exactly one gold supporting sentence contains the normalized answer;
6. no non-supporting sentence contains the normalized answer;
7. after deleting the answer-bearing support, at least one gold support remains;
8. the remaining L2 evidence does not contain the normalized answer;
9. prompt length is at most 24,000 characters at L0.

## Four levels

- L0 (A): question plus the original ten-paragraph distractor context.
- L1 (A): question plus only the official gold supporting sentences.
- L2 (P): question plus the remaining gold supporting sentence(s), after the
  unique answer-bearing supporting sentence is removed.
- L3 (U): question with no evidence sentence.

The question and response contract are identical at all levels. Only visible
evidence changes.

## Response contract and automatic scoring

The endpoint must return one JSON object:

```json
{"status":"answer|insufficient","answer":"text or empty","reason":"brief explanation"}
```

At L0/L1, an appropriate response has `status=answer` and normalized exact
match with the official answer. At L2/L3, an appropriate response has
`status=insufficient` and an empty `answer`. Primary outcomes are:

- answer exact match at L0/L1;
- insufficient-status accuracy at L2/L3;
- unsupported-answer emission rate at L2/L3;
- automatic appropriate response rate by level;
- IDU and CFO across each matched endpoint-question trajectory.

JSON parse failure is reported separately and counted as inappropriate in the
strict primary analysis. A sensitivity analysis may report parseable content
after conservative extraction, but it must not replace the prespecified strict
result.

## Interpretation limits

The experiment measures prompt-evidence sufficiency under an explicit
context-only instruction. It does not show that a model lacks the answer in
its parameters. HotpotQA supporting facts are public annotations, but the
four-level transformation remains a derived evaluation and is released with
full source IDs and deletion provenance.

