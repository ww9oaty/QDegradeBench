# Zenodo upload information

## Resource type

Dataset

## Title

QDegradeBench: Matched Information-Degradation Chains and Human-Labeled LLM Responses

## Publication date

2026-10-09

## Version

1.0.2

## Creators, in order

1. Wenyue Wang — Zhejiang University of Science and Technology
2. Zhijie Lin — Zhejiang University of Science and Technology
3. Yindan Li — Taizhou University
4. Chufei Weng — Taizhou University
5. Jiehui Ju — Zhejiang University of Science and Technology
6. Lei Zhao — Zhejiang University

## Description

QDegradeBench is a research dataset for evaluating large language model behavior under progressive loss of task-critical information. It contains 32 Chinese base tasks, each represented by a matched four-level information-degradation chain, yielding 128 prompts. Four API endpoints produced 512 responses. Every response has a final human-confirmed behavior label, and a stratified sample of 128 responses was independently reviewed by a second human annotator.

The package also contains a public English transfer study constructed from 24 E2E NLG Challenge records. Its 96 matched prompts produced 192 responses from two endpoints. The released external-validation records include source and omission metadata, final human-confirmed labels, and a structured L2 audit of unsupported required values, complete or partial missing-field acknowledgment, and factual-instruction compliance. English review used AI-assisted Chinese translations and preliminary suggestions followed by explicit human confirmation; it was not independent blinded English annotation.

The package includes annotation guidance, experimental and collection metadata, integrity records, and standard-library Python scripts that reproduce ARR, UAR, IDU, critical-information failure onset, agreement, Cohen's kappa, and the external L2 audit rates. AI-generated preliminary labels, reviewer identities, private notes, credentials, and service configuration are excluded.

## Keywords

large language models; information sufficiency; prompt degradation; clarification; abstention; hallucination; reliability evaluation; benchmark

## License

Creative Commons Attribution 4.0 International

## Funding

The Premium Online Open Course Project of Zhejiang University of Science and Technology (2022-xk6)

## Related identifier

https://github.com/ww9oaty/QDegradeBench — Is supplement to this upload

## DOI setting

Select “No” for an existing DOI, then use “Get a DOI now” to reserve a Zenodo DOI before publication. Insert that DOI into the paper's Data Availability section. Upload `QDegradeBench_reproducibility_package.zip`. Do not publish until the author order, version 1.0.2, license, uploaded ZIP, and record preview have been checked.
