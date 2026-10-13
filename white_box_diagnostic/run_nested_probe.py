from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import run_grouped_probe as base


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "results" / "grouped_probe_qwen3_1_7b"


def nested_layer_oof(hidden: np.ndarray, y: np.ndarray, folds: np.ndarray):
    probabilities = np.empty(len(y), dtype=np.float64)
    selections = []
    for outer_fold in sorted(set(folds.tolist())):
        outer_train = folds != outer_fold
        outer_test = folds == outer_fold
        inner_scores = []
        for layer in range(hidden.shape[1]):
            inner_prob = base.fit_numeric_oof(
                hidden[outer_train, layer, :], y[outer_train], folds[outer_train]
            )
            inner_scores.append(
                base.metrics(y[outer_train], inner_prob)["balanced_accuracy"]
            )
        selected_layer = int(np.argmax(np.asarray(inner_scores)))
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=1.0,
                solver="liblinear",
                max_iter=2_000,
                random_state=base.SEED,
            ),
        )
        model.fit(hidden[outer_train, selected_layer, :], y[outer_train])
        probabilities[outer_test] = model.predict_proba(
            hidden[outer_test, selected_layer, :]
        )[:, 1]
        selections.append(
            {
                "outer_fold": int(outer_fold),
                "selected_layer": selected_layer,
                "inner_balanced_accuracy": float(inner_scores[selected_layer]),
            }
        )
    return probabilities, selections


def paired_group_bootstrap(frame: pd.DataFrame, iterations: int = 10_000):
    rng = np.random.default_rng(base.SEED)
    groups = sorted(frame["base_task"].unique().tolist())
    methods = [
        "length_probability",
        "tfidf_probability",
        "hidden_final_probability",
        "hidden_nested_probability",
    ]
    draws = {method: [] for method in methods}
    differences = {"nested_minus_length": [], "nested_minus_tfidf": []}
    for _ in range(iterations):
        sampled = rng.choice(groups, size=len(groups), replace=True)
        indices = np.concatenate(
            [frame.index[frame["base_task"] == group].to_numpy() for group in sampled]
        )
        y = frame.loc[indices, "label"].to_numpy()
        values = {}
        for method in methods:
            values[method] = base.metrics(y, frame.loc[indices, method].to_numpy())
            draws[method].append(values[method]["balanced_accuracy"])
        differences["nested_minus_length"].append(
            values["hidden_nested_probability"]["balanced_accuracy"]
            - values["length_probability"]["balanced_accuracy"]
        )
        differences["nested_minus_tfidf"].append(
            values["hidden_nested_probability"]["balanced_accuracy"]
            - values["tfidf_probability"]["balanced_accuracy"]
        )
    return {
        "balanced_accuracy_95_intervals": {
            method: [
                float(np.quantile(values, 0.025)),
                float(np.quantile(values, 0.975)),
            ]
            for method, values in draws.items()
        },
        "balanced_accuracy_difference_95_intervals": {
            name: [
                float(np.quantile(values, 0.025)),
                float(np.quantile(values, 0.975)),
            ]
            for name, values in differences.items()
        },
    }


def main():
    records = base.read_jsonl(base.DATA_PATH)
    archive = np.load(base.HIDDEN_PATH)
    hidden = archive["hidden"]
    sample_ids = np.asarray([str(item["sample_id"]) for item in records])
    if not np.array_equal(sample_ids, archive["sample_ids"].astype(str)):
        raise RuntimeError("Hidden-state and dataset sample IDs are misaligned")

    y = np.asarray([int(item["binary_sufficiency"]) for item in records])
    base_tasks = np.asarray([str(item["base_task"]) for item in records])
    folds = base.make_balanced_folds(base_tasks)
    nested_probability, selections = nested_layer_oof(hidden, y, folds)

    prediction_path = OUTPUT_DIR / "oof_predictions.csv"
    frame = pd.read_csv(prediction_path)
    frame["hidden_nested_probability"] = nested_probability
    frame.to_csv(prediction_path, index=False, encoding="utf-8-sig")

    result = {
        "analysis_status": "exploratory",
        "selection": (
            "For each outer fold, the layer was selected only with grouped "
            "inner cross-validation on the outer-training tasks."
        ),
        "point_estimates": {
            method: base.metrics(y, frame[method].to_numpy())
            for method in [
                "length_probability",
                "tfidf_probability",
                "hidden_final_probability",
                "hidden_nested_probability",
            ]
        },
        "nested_layer_selections": selections,
        **paired_group_bootstrap(frame),
        "interpretive_limit": (
            "Decodability is an association and does not establish that the "
            "model uses this signal causally when generating an answer."
        ),
    }
    output_path = OUTPUT_DIR / "nested_probe_summary.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"PASS: wrote {output_path}")


if __name__ == "__main__":
    main()
