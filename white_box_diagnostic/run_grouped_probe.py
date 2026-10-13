"""Grouped answerability probe with length and surface-text baselines.

Primary comparison: final-layer prompt-end hidden state versus length and
character TF-IDF baselines. All four levels of a base task stay in one fold.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "probe_prompts_128.jsonl"
HIDDEN_PATH = ROOT / "results" / "probe_qwen3_1_7b" / "prompt_end_hidden_128.npz"
OUTPUT_DIR = ROOT / "results" / "grouped_probe_qwen3_1_7b"
SEED = 20260916
BOOTSTRAP_ITERATIONS = 10_000


def read_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def task_family(base_task: str) -> str:
    family = base_task[:2]
    if family not in {"CD", "CG", "DP", "NR"}:
        raise ValueError(f"Unknown task family: {base_task}")
    return family


def make_balanced_folds(base_tasks: np.ndarray) -> np.ndarray:
    """Create eight folds, each holding one base task from each task family."""
    by_family: dict[str, list[str]] = defaultdict(list)
    for base in sorted(set(base_tasks.tolist())):
        by_family[task_family(base)].append(base)
    if set(by_family) != {"CD", "CG", "DP", "NR"}:
        raise RuntimeError(f"Unexpected task families: {sorted(by_family)}")
    if any(len(values) != 8 for values in by_family.values()):
        raise RuntimeError(f"Expected eight tasks per family: {by_family}")
    fold_for_base = {}
    for family in sorted(by_family):
        for fold, base in enumerate(sorted(by_family[family])):
            fold_for_base[base] = fold
    return np.asarray([fold_for_base[base] for base in base_tasks], dtype=np.int32)


def metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    prediction = (probability >= 0.5).astype(np.int32)
    return {
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "macro_f1": float(f1_score(y, prediction, average="macro")),
        "auroc": float(roc_auc_score(y, probability)),
    }


def fit_numeric_oof(
    features: np.ndarray, y: np.ndarray, folds: np.ndarray
) -> np.ndarray:
    probabilities = np.empty(len(y), dtype=np.float64)
    for fold in sorted(set(folds.tolist())):
        train = folds != fold
        test = folds == fold
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=1.0,
                solver="liblinear",
                max_iter=2_000,
                random_state=SEED,
            ),
        )
        model.fit(features[train], y[train])
        probabilities[test] = model.predict_proba(features[test])[:, 1]
    return probabilities


def fit_text_oof(texts: np.ndarray, y: np.ndarray, folds: np.ndarray) -> np.ndarray:
    probabilities = np.empty(len(y), dtype=np.float64)
    for fold in sorted(set(folds.tolist())):
        train = folds != fold
        test = folds == fold
        vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 5),
            min_df=2,
            max_features=5_000,
            sublinear_tf=True,
        )
        x_train = vectorizer.fit_transform(texts[train])
        x_test = vectorizer.transform(texts[test])
        classifier = LogisticRegression(
            C=1.0,
            solver="liblinear",
            max_iter=2_000,
            random_state=SEED,
        )
        classifier.fit(x_train, y[train])
        probabilities[test] = classifier.predict_proba(x_test)[:, 1]
    return probabilities


def group_bootstrap(
    frame: pd.DataFrame, methods: list[str]
) -> tuple[dict[str, dict[str, list[float]]], dict[str, list[float]]]:
    rng = np.random.default_rng(SEED)
    groups = sorted(frame["base_task"].unique().tolist())
    draws = {method: defaultdict(list) for method in methods}
    differences = defaultdict(list)
    for _ in range(BOOTSTRAP_ITERATIONS):
        sampled = rng.choice(groups, size=len(groups), replace=True)
        indices = np.concatenate(
            [frame.index[frame["base_task"] == group].to_numpy() for group in sampled]
        )
        y = frame.loc[indices, "label"].to_numpy()
        current = {}
        for method in methods:
            current[method] = metrics(y, frame.loc[indices, method].to_numpy())
            for name, value in current[method].items():
                draws[method][name].append(value)
        for baseline in ["length_probability", "tfidf_probability"]:
            key = f"hidden_minus_{baseline}"
            differences[key].append(
                current["hidden_final_probability"]["balanced_accuracy"]
                - current[baseline]["balanced_accuracy"]
            )
    intervals = {}
    for method, metric_draws in draws.items():
        intervals[method] = {}
        for name, values in metric_draws.items():
            intervals[method][name] = [
                float(np.quantile(values, 0.025)),
                float(np.quantile(values, 0.975)),
            ]
    difference_intervals = {
        name: [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]
        for name, values in differences.items()
    }
    return intervals, difference_intervals


def main() -> None:
    records = read_jsonl(DATA_PATH)
    archive = np.load(HIDDEN_PATH)
    hidden = archive["hidden"]
    token_counts = archive["token_counts"]
    stored_ids = archive["sample_ids"].astype(str)
    sample_ids = np.asarray([str(item["sample_id"]) for item in records])
    if not np.array_equal(sample_ids, stored_ids):
        raise RuntimeError("Hidden-state and dataset sample IDs are misaligned")
    if hidden.shape != (128, 29, 2048):
        raise RuntimeError(f"Unexpected hidden-state shape: {hidden.shape}")

    labels = np.asarray([int(item["binary_sufficiency"]) for item in records])
    base_tasks = np.asarray([str(item["base_task"]) for item in records])
    texts = np.asarray([str(item["prompt"]) for item in records])
    character_counts = np.asarray(
        [int(item["character_count"]) for item in records], dtype=np.float64
    )
    folds = make_balanced_folds(base_tasks)
    if any(len(set(base_tasks[folds == fold])) != 4 for fold in range(8)):
        raise RuntimeError("Each fold must contain four complete base-task groups")

    length_features = np.column_stack([character_counts, token_counts.astype(float)])
    length_probability = fit_numeric_oof(length_features, labels, folds)
    tfidf_probability = fit_text_oof(texts, labels, folds)
    hidden_final_probability = fit_numeric_oof(hidden[:, -1, :], labels, folds)

    layer_rows = []
    for layer in range(hidden.shape[1]):
        probability = fit_numeric_oof(hidden[:, layer, :], labels, folds)
        result = metrics(labels, probability)
        layer_rows.append({"layer": layer, **result})
    layer_frame = pd.DataFrame(layer_rows)

    frame = pd.DataFrame(
        {
            "sample_id": sample_ids,
            "base_task": base_tasks,
            "task_type": [str(item["task_type"]) for item in records],
            "level": [str(item["level"]) for item in records],
            "answerability": [str(item["answerability"]) for item in records],
            "label": labels,
            "fold": folds,
            "character_count": character_counts.astype(int),
            "token_count": token_counts,
            "length_probability": length_probability,
            "tfidf_probability": tfidf_probability,
            "hidden_final_probability": hidden_final_probability,
        }
    )
    methods = [
        "length_probability",
        "tfidf_probability",
        "hidden_final_probability",
    ]
    point_estimates = {
        method: metrics(labels, frame[method].to_numpy()) for method in methods
    }
    intervals, difference_intervals = group_bootstrap(frame, methods)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT_DIR / "oof_predictions.csv", index=False, encoding="utf-8-sig")
    layer_frame.to_csv(OUTPUT_DIR / "layerwise_metrics.csv", index=False)
    summary = {
        "analysis_status": "exploratory",
        "primary_feature": "final-layer prompt-end hidden state",
        "label": "A versus P_or_U",
        "unit": "prompt, grouped by base task",
        "folds": 8,
        "fold_design": "one complete base task from each of four task families per fold",
        "logistic_regression_C": 1.0,
        "decision_threshold": 0.5,
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "point_estimates": point_estimates,
        "group_bootstrap_95_intervals": intervals,
        "balanced_accuracy_difference_95_intervals": difference_intervals,
        "best_descriptive_layer": int(
            layer_frame.loc[layer_frame["balanced_accuracy"].idxmax(), "layer"]
        ),
        "best_descriptive_layer_balanced_accuracy": float(
            layer_frame["balanced_accuracy"].max()
        ),
        "interpretive_limit": (
            "Decodability does not show that the model uses the signal causally. "
            "Layerwise results are secondary and descriptive."
        ),
    }
    (OUTPUT_DIR / "probe_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"PASS: wrote grouped-probe results to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
