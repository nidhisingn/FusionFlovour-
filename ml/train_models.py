"""Improved training pipeline for recipe prediction.

Enhancements over the earlier version:
1) Uses richer features from ingredients + metadata (cuisines, diets, dish types)
2) Supports grouped labels so the model can learn broader recipe families
3) Evaluates with cross-validation instead of a single tiny validation split
4) Trains multiple complementary models on TF-IDF text features
5) Builds a hybrid retrieval index for ingredient overlap / recommendation reranking
6) Saves detailed metrics and artifacts for inference

Run:
  cd ml
  python3 train_models.py
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, top_k_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.multiclass import OneVsRestClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer, FunctionTransformer
from sklearn.svm import LinearSVC


ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
DEFAULT_CV_SPLITS = 3
TOP_K = 3

GROUP_KEYWORDS: Dict[str, List[str]] = {
    "soup": ["soup", "broth", "stew", "bisque", "chowder"],
    "salad": ["salad", "slaw"],
    "curry": ["curry", "masala", "korma", "vindaloo"],
    "rice": ["rice", "pilaf", "biryani", "risotto", "jambalaya", "quinoa"],
    "pasta_noodles": ["pasta", "noodle", "macaroni", "spaghetti", "rotini"],
    "dip_spread": ["dip", "hummus", "guacamole", "spread", "salsa", "pesto"],
    "breakfast": ["frittata", "omelette", "muffin", "smoothie", "breakfast"],
    "wrap_roll": ["wrap", "roll", "enchilada", "taco", "quesadilla"],
    "side_dish": ["side", "broccoli", "kale", "sprouts"],
}


def _safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _normalize_token(value: str) -> str:
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9+\s-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _split_pipe(value: Any) -> List[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    return [_normalize_token(part) for part in str(value).split("|") if _normalize_token(part)]


def infer_recipe_group(recipe_name: str, dish_types: List[str], cuisines: List[str]) -> str:
    text = " ".join([_normalize_token(recipe_name), *dish_types, *cuisines])
    for group_name, keywords in GROUP_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return group_name
    return "misc_recipe"


def augment_minority_rows(df: pd.DataFrame, min_samples_per_group: int = 3) -> pd.DataFrame:
    """Duplicate low-frequency grouped classes with tiny ingredient perturbations.

    This is not a substitute for collecting more data, but it stabilizes the demo
    training pipeline when class counts are extremely low.
    """
    records: List[Dict[str, Any]] = []
    counts = df["target_group"].value_counts().to_dict()
    for _, row in df.iterrows():
        records.append(row.to_dict())

    for group_name, count in counts.items():
        if count >= min_samples_per_group:
            continue
        group_rows = df[df["target_group"] == group_name]
        needed = min_samples_per_group - count
        for idx in range(needed):
            source = group_rows.iloc[idx % len(group_rows)].to_dict()
            ingredients = list(source["ingredient_list"])
            if len(ingredients) > 4:
                ingredients = ingredients[:-1]
            source["ingredient_list"] = ingredients
            source["ingredients"] = "|".join(ingredients)
            source["augmented"] = True
            records.append(source)

    out = pd.DataFrame(records)
    return out.reset_index(drop=True)


def load_dataset(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required = {"recipe", "ingredients"}
    if not required.issubset(df.columns):
        raise ValueError("recipes.csv must contain columns: recipe, ingredients")

    for col in ["recipe", "ingredients", "cuisines", "diets", "dishTypes"]:
        if col not in df.columns:
            df[col] = ""

    df = df.dropna(subset=["recipe", "ingredients"]).copy()
    df["recipe"] = df["recipe"].astype(str).str.strip()
    df["ingredients"] = df["ingredients"].astype(str)
    df = df[df["recipe"].str.len() > 0]
    df = df[df["ingredients"].str.len() > 0]

    df["ingredient_list"] = df["ingredients"].apply(_split_pipe)
    df["cuisine_list"] = df["cuisines"].apply(_split_pipe)
    df["diet_list"] = df["diets"].apply(_split_pipe)
    df["dish_type_list"] = df["dishTypes"].apply(_split_pipe)
    df["target_group"] = df.apply(
        lambda row: infer_recipe_group(row["recipe"], row["dish_type_list"], row["cuisine_list"]),
        axis=1,
    )
    df["augmented"] = False
    return augment_minority_rows(df)


def build_training_text(df: pd.DataFrame) -> pd.DataFrame:
    def join_prefixed(prefix: str, values: List[str]) -> str:
        return " ".join([f"{prefix}_{value.replace(' ', '_')}" for value in values])

    df = df.copy()
    df["ingredient_text"] = df["ingredient_list"].apply(lambda vals: " ".join(vals))
    df["metadata_text"] = df.apply(
        lambda row: " ".join(
            part
            for part in [
                join_prefixed("cuisine", row["cuisine_list"]),
                join_prefixed("diet", row["diet_list"]),
                join_prefixed("dish", row["dish_type_list"]),
            ]
            if part
        ),
        axis=1,
    )
    df["combined_text"] = (
        df["ingredient_text"].fillna("")
        + " "
        + df["metadata_text"].fillna("")
        + " title_"
        + df["recipe"].apply(lambda x: _normalize_token(x).replace(" ", "_"))
    ).str.strip()
    return df


def make_labels(df: pd.DataFrame) -> Tuple[np.ndarray, LabelEncoder]:
    le = LabelEncoder()
    y = le.fit_transform(df["target_group"])
    return y, le


def build_sparse_metadata_features(df: pd.DataFrame) -> MultiLabelBinarizer:
    labels = [
        [
            *(f"cuisine:{item}" for item in row["cuisine_list"]),
            *(f"diet:{item}" for item in row["diet_list"]),
            *(f"dish:{item}" for item in row["dish_type_list"]),
        ]
        for _, row in df.iterrows()
    ]
    mlb = MultiLabelBinarizer(sparse_output=True)
    mlb.fit(labels)
    return mlb


def metadata_transform(df: pd.DataFrame, mlb: MultiLabelBinarizer):
    labels = [
        [
            *(f"cuisine:{item}" for item in row["cuisine_list"]),
            *(f"diet:{item}" for item in row["diet_list"]),
            *(f"dish:{item}" for item in row["dish_type_list"]),
        ]
        for _, row in df.iterrows()
    ]
    return mlb.transform(labels)


def select_ingredient_text(frame: pd.DataFrame):
    return frame["ingredient_text"]


def select_combined_text(frame: pd.DataFrame):
    return frame["combined_text"]


def transform_metadata_frame(frame: pd.DataFrame, mlb: MultiLabelBinarizer):
    return metadata_transform(frame, mlb)


class MetadataTransformer:
    def __init__(self, mlb: MultiLabelBinarizer):
        self.mlb = mlb

    def __call__(self, frame: pd.DataFrame):
        return transform_metadata_frame(frame, self.mlb)


def build_pipeline(base_model: Any, metadata_mlb: MultiLabelBinarizer) -> Pipeline:
    ingredient_pipe = Pipeline(
        steps=[
            (
                "selector",
                FunctionTransformer(select_ingredient_text, validate=False),
            ),
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    sublinear_tf=True,
                ),
            ),
        ]
    )

    combined_pipe = Pipeline(
        steps=[
            (
                "selector",
                FunctionTransformer(select_combined_text, validate=False),
            ),
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    sublinear_tf=True,
                ),
            ),
        ]
    )

    meta_pipe = Pipeline(
        steps=[
            (
                "metadata",
                FunctionTransformer(MetadataTransformer(metadata_mlb), validate=False),
            )
        ]
    )

    union = FeatureUnion(
        transformer_list=[
            ("ingredient_tfidf", ingredient_pipe),
            ("combined_tfidf", combined_pipe),
            ("metadata_sparse", meta_pipe),
        ]
    )
    return Pipeline(steps=[("features", union), ("model", base_model)])


def compute_topk(y_true: np.ndarray, y_score: np.ndarray, k: int = TOP_K) -> float:
    labels = np.arange(y_score.shape[1])
    return float(top_k_accuracy_score(y_true, y_score, k=min(k, y_score.shape[1]), labels=labels))


def score_model_outputs(model: Any, X_val: pd.DataFrame, y_val: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    y_pred = model.predict(X_val)
    if hasattr(model, "predict_proba"):
        y_score = np.asarray(model.predict_proba(X_val))
    elif hasattr(model, "decision_function"):
        y_score = np.asarray(model.decision_function(X_val))
        if y_score.ndim == 1:
            y_score = np.vstack([-y_score, y_score]).T
    else:
        n_classes = int(np.max(y_val)) + 1
        y_score = np.zeros((X_val.shape[0], n_classes), dtype=float)
        y_score[np.arange(X_val.shape[0]), y_pred] = 1.0
    return y_pred, y_score


@dataclass
class ModelResult:
    name: str
    fitted_model: Any
    cv_accuracy_mean: float
    cv_top3_mean: float
    fold_metrics: List[Dict[str, float]]


def evaluate_models_cv(df: pd.DataFrame, y: np.ndarray, metadata_mlb: MultiLabelBinarizer) -> List[ModelResult]:
    class_counts = Counter(y)
    min_class_size = min(class_counts.values()) if class_counts else 1
    n_splits = max(2, min(DEFAULT_CV_SPLITS, min_class_size))
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    model_defs: List[Tuple[str, Any]] = [
        (
            "logreg_ovr",
            OneVsRestClassifier(
                LogisticRegression(max_iter=3000, solver="liblinear", class_weight="balanced", C=4.0)
            ),
        ),
        (
            "linear_svc_calibrated_ovr",
            OneVsRestClassifier(
                CalibratedClassifierCV(
                    estimator=LinearSVC(C=1.5, class_weight="balanced"),
                    cv=2,
                )
            ),
        ),
        ("multinomial_nb", MultinomialNB(alpha=0.2)),
        (
            "random_forest",
            RandomForestClassifier(
                n_estimators=300,
                max_depth=24,
                min_samples_leaf=1,
                min_samples_split=2,
                random_state=42,
                n_jobs=-1,
                class_weight="balanced_subsample",
            ),
        ),
        (
            "sklearn_mlp",
            MLPClassifier(
                hidden_layer_sizes=(256, 128),
                activation="relu",
                alpha=1e-4,
                batch_size=32,
                learning_rate_init=1e-3,
                max_iter=250,
                early_stopping=True,
                n_iter_no_change=12,
                random_state=42,
            ),
        ),
    ]

    results: List[ModelResult] = []
    for name, base_model in model_defs:
        fold_metrics: List[Dict[str, float]] = []
        for train_idx, val_idx in cv.split(df, y):
            X_train = df.iloc[train_idx]
            X_val = df.iloc[val_idx]
            y_train = y[train_idx]
            y_val = y[val_idx]

            pipe = build_pipeline(clone(base_model), metadata_mlb)
            pipe.fit(X_train, y_train)
            y_pred, y_score = score_model_outputs(pipe, X_val, y_val)

            fold_metrics.append(
                {
                    "accuracy": float(accuracy_score(y_val, y_pred)),
                    "top3": compute_topk(y_val, y_score, TOP_K),
                }
            )

        final_model = build_pipeline(clone(base_model), metadata_mlb)
        final_model.fit(df, y)
        results.append(
            ModelResult(
                name=name,
                fitted_model=final_model,
                cv_accuracy_mean=float(np.mean([m["accuracy"] for m in fold_metrics])),
                cv_top3_mean=float(np.mean([m["top3"] for m in fold_metrics])),
                fold_metrics=fold_metrics,
            )
        )
    return results


def build_retrieval_index(df: pd.DataFrame) -> Dict[str, Any]:
    grouped_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for _, row in df.iterrows():
        grouped_rows[row["target_group"]].append(
            {
                "recipe": row["recipe"],
                "ingredients": row["ingredient_list"],
                "cuisines": row["cuisine_list"],
                "diets": row["diet_list"],
                "dishTypes": row["dish_type_list"],
            }
        )

    return {
        "groups": grouped_rows,
        "all_recipes": [
            {
                "recipe": row["recipe"],
                "target_group": row["target_group"],
                "ingredients": row["ingredient_list"],
                "cuisines": row["cuisine_list"],
                "diets": row["diet_list"],
                "dishTypes": row["dish_type_list"],
            }
            for _, row in df.iterrows()
            if not row.get("augmented", False)
        ],
    }


def save_artifacts(
    df: pd.DataFrame,
    label_encoder: LabelEncoder,
    metadata_mlb: MultiLabelBinarizer,
    results: List[ModelResult],
    retrieval_index: Dict[str, Any],
) -> Dict[str, Any]:
    _safe_mkdir(ARTIFACT_DIR)

    best = max(results, key=lambda r: (r.cv_top3_mean, r.cv_accuracy_mean))
    for result in results:
        joblib.dump(result.fitted_model, os.path.join(ARTIFACT_DIR, f"{result.name}.joblib"))

    joblib.dump(label_encoder, os.path.join(ARTIFACT_DIR, "label_encoder.joblib"))
    joblib.dump(metadata_mlb, os.path.join(ARTIFACT_DIR, "metadata_mlb.joblib"))
    joblib.dump(retrieval_index, os.path.join(ARTIFACT_DIR, "retrieval_index.joblib"))

    # Keep legacy filename for backend compatibility, though inference no longer depends on it.
    ingredient_mlb = MultiLabelBinarizer()
    ingredient_mlb.fit(df["ingredient_list"])
    joblib.dump(ingredient_mlb, os.path.join(ARTIFACT_DIR, "mlb_ingredients.joblib"))

    metrics_out = {
        "n_rows": int(len(df)),
        "n_original_rows": int((~df["augmented"]).sum()),
        "n_augmented_rows": int(df["augmented"].sum()),
        "n_group_classes": int(len(label_encoder.classes_)),
        "target_groups": list(label_encoder.classes_),
        "cv_strategy": {"type": "StratifiedKFold", "splits": int(max(2, min(DEFAULT_CV_SPLITS, min(Counter(label_encoder.transform(df['target_group'])).values()))))},
        "results": [
            {
                "name": result.name,
                "cv_accuracy_mean": result.cv_accuracy_mean,
                "cv_top3_mean": result.cv_top3_mean,
                "fold_metrics": result.fold_metrics,
                "artifact": f"{result.name}.joblib",
            }
            for result in results
        ],
        "best": {
            "name": best.name,
            "cv_accuracy_mean": best.cv_accuracy_mean,
            "cv_top3_mean": best.cv_top3_mean,
            "artifact": f"{best.name}.joblib",
        },
        "feature_strategy": {
            "ingredients": "TF-IDF unigram+bigram",
            "metadata": ["cuisines", "diets", "dishTypes"],
            "target": "Grouped recipe families",
            "inference": "Model probabilities + retrieval reranking",
        },
        "dataset_recommendation": "For production quality, collect many more recipes per group and replace synthetic augmentation with true examples.",
    }

    with open(os.path.join(ARTIFACT_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_out, f, indent=2)
    return metrics_out


def main() -> None:
    csv_path = os.path.join(os.path.dirname(__file__), "recipes.csv")
    df = load_dataset(csv_path)
    if df.empty:
        raise RuntimeError("recipes.csv has no usable rows")

    df = build_training_text(df)
    y, label_encoder = make_labels(df)
    metadata_mlb = build_sparse_metadata_features(df)
    results = evaluate_models_cv(df, y, metadata_mlb)
    retrieval_index = build_retrieval_index(df)
    metrics = save_artifacts(df, label_encoder, metadata_mlb, results, retrieval_index)

    print(f"Dataset rows used: {metrics['n_rows']} (original={metrics['n_original_rows']}, augmented={metrics['n_augmented_rows']})")
    print(f"Grouped classes: {metrics['n_group_classes']}")
    print("Model summary:")
    for result in metrics["results"]:
        print(
            f"- {result['name']}: cv_accuracy={result['cv_accuracy_mean']:.4f}, "
            f"cv_top3={result['cv_top3_mean']:.4f}"
        )
    print(
        f"Best model: {metrics['best']['name']} "
        f"(cv_top3={metrics['best']['cv_top3_mean']:.4f})"
    )
    print(f"Artifacts saved to: {ARTIFACT_DIR}")


if __name__ == "__main__":
    main()