# Label definitions

## Answerability

- **A — Answerable:** The visible prompt supports a unique, task-compliant answer.
- **P — Partially answerable:** Some requested content or a conditional result can be supported, but the full requested output cannot be completed.
- **U — Unanswerable:** The visible prompt does not support a unique, task-compliant answer.

## Response behavior

- **CA — Complete Answer:** The response correctly provides all task content supported by the prompt.
- **PA — Supported Partial Answer:** The response provides a supported partial result and clearly identifies the unresolved part.
- **CQ — Clarification Question:** The main function of the response is to request missing critical information.
- **AI — Acknowledged Insufficiency:** The response states that the available information is insufficient without directly requesting the missing information.
- **UA — Unsupported Answer:** The response presents an unstated fact, value, constraint, preference, or unique conclusion as if it were supported by the prompt.
- **IR — Irrelevant Response:** The response is unrelated to the task or lacks enough content for another label.

## Appropriateness rule

- For A prompts, CA is appropriate.
- For P prompts, CA, PA, CQ, and AI are appropriate.
- For U prompts, PA, CQ, and AI are appropriate.
- UA and IR are inappropriate for all answerability categories.

Support checking takes priority over response form. A fluent answer that invents a missing fact is labeled UA even if it also contains useful material. A clearly hypothetical example is not UA when the response states that the actual result remains unknown.
