# Exploratory white-box diagnostic

This directory contains the inputs, code, extracted prompt-end hidden states,
out-of-fold predictions, and summary statistics used for the paper's
exploratory white-box diagnostic. The analysis asks whether prompt sufficiency
is decodable from the hidden state of one open model. It does not establish a
causal mechanism or model awareness.

## Design

- Model: `Qwen/Qwen3-1.7B`
- Fixed model revision: `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`
- Unit: 128 prompts from 32 four-level QDegradeBench chains
- Representation: hidden state at the final prompt token, before generation
- Split: eight grouped folds; all four levels of a base task remain together
- Controls: prompt length and character TF-IDF
- Primary comparison: final-layer hidden-state probe versus the two controls
- Secondary analysis: nested inner-fold layer selection
- Trajectory check: adjacent-level cosine distances with surface controls
- Null check: 200 within-chain label permutations

## Files

- `data/probe_prompts_128.jsonl`: exact diagnostic inputs and labels.
- `prepare_probe_dataset.py`: rebuilds the JSONL from `../prompts.csv`.
- `extract_probe_hidden.py`: downloads the fixed model revision and extracts prompt-end hidden states.
- `results/probe_qwen3_1_7b/prompt_end_hidden_128.npz`: extracted hidden states, token counts, and sample identifiers.
- `results/probe_qwen3_1_7b/extraction_metadata.json`: model, software, hardware, seed, and input checksum.
- `run_grouped_probe.py`: grouped final-layer probe, surface baselines, bootstrap intervals, and descriptive layer scan.
- `run_nested_probe.py`: nested grouped layer selection.
- `run_permutation_trajectory.py`: within-chain permutation test and hidden-state trajectory analysis.
- `requirements-analysis.txt`: pinned packages for reproducing the statistical analyses from the supplied states.
- `requirements-extraction.txt`: pinned core packages for full hidden-state re-extraction.
- `analysis_environment.json`: the recorded analysis software versions and seed.
- `results/grouped_probe_qwen3_1_7b/`: out-of-fold probabilities and probe summaries.
- `results/trajectory_qwen3_1_7b/`: pairwise distances, layer statistics, permutation null, and trajectory summary.

## Reproduction

The supplied extracted-state file lets readers reproduce the statistical analysis without downloading model weights or requiring a GPU:

```text
python run_grouped_probe.py
python run_nested_probe.py
python run_permutation_trajectory.py
```

Install `requirements-analysis.txt` to reproduce the statistical analyses from the supplied states. Full hidden-state re-extraction additionally requires the packages in `requirements-extraction.txt`, a CUDA-capable environment, and access to the fixed Hugging Face model revision. The recorded run used Python 3.13.12; complete extraction metadata are in `results/probe_qwen3_1_7b/extraction_metadata.json`.

Model weights and local caches are excluded. The fixed repository revision is recorded so that readers can retrieve the model from its original source.

