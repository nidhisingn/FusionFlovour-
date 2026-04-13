"""Prediction entrypoint used by the Spring Boot backend.

This version supports the improved training pipeline with:
- grouped recipe-family prediction
- richer TF-IDF + metadata-based sklearn pipelines
- retrieval-style reranking over actual recipes
- ingredient normalization, substitutions, diet hints, and personalization
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np


def select_ingredient_text(frame):
    return frame["ingredient_text"]


def select_combined_text(frame):
    return frame["combined_text"]


def metadata_transform(frame, mlb):
    labels = [
        [
            *(f"cuisine:{item}" for item in row["cuisine_list"]),
            *(f"diet:{item}" for item in row["diet_list"]),
            *(f"dish:{item}" for item in row["dish_type_list"]),
        ]
        for _, row in frame.iterrows()
    ]
    return mlb.transform(labels)


def transform_metadata_frame(frame, mlb):
    return metadata_transform(frame, mlb)


class MetadataTransformer:
    def __init__(self, mlb):
        self.mlb = mlb

    def __call__(self, frame):
        return transform_metadata_frame(frame, self.mlb)


BASE_DIR = os.path.dirname(__file__)
ARTIFACT_DIR = os.path.join(BASE_DIR, "artifacts")

INGREDIENT_SYNONYMS = {
    "capsicum": "bell pepper",
    "shimla mirch": "bell pepper",
    "dhania": "coriander",
    "coriander leaves": "coriander",
    "curd": "yogurt",
    "dahi": "yogurt",
    "paneer": "cottage cheese",
    "spring onion": "green onion",
    "scallion": "green onion",
    "maida": "flour",
    "atta": "wheat flour",
    "chilli": "chili",
    "garbanzo": "chickpea",
}

SUBSTITUTION_MAP = {
    "milk": ["oat milk", "almond milk", "soy milk"],
    "cheese": ["paneer", "tofu", "nutritional yeast"],
    "butter": ["olive oil", "vegan butter", "ghee"],
    "egg": ["flax egg", "mashed banana", "yogurt"],
    "bread": ["gluten-free bread", "lettuce wrap", "rice paper"],
    "soy sauce": ["tamari", "coconut aminos", "salt + lemon"],
    "cream": ["cashew cream", "hung curd", "coconut cream"],
}

DIET_KEYWORDS = {
    "vegan": {"paneer", "cheese", "milk", "butter", "cream", "yogurt", "egg", "chicken", "beef", "pork", "fish"},
    "vegetarian": {"chicken", "beef", "pork", "fish", "shrimp", "prawn", "crab", "mutton"},
    "high-protein": {"chicken", "egg", "paneer", "tofu", "lentil", "beans", "chickpea", "yogurt"},
    "balanced": set(),
}


def _artifact(path: str) -> str:
    return os.path.join(ARTIFACT_DIR, path)


def normalize_ingredient(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(value).strip().lower())
    return INGREDIENT_SYNONYMS.get(cleaned, cleaned)


def normalize_ingredients(values: List[str]) -> Tuple[List[str], List[Dict[str, str]]]:
    normalized: List[str] = []
    mappings: List[Dict[str, str]] = []
    for value in values:
        mapped = normalize_ingredient(value)
        normalized.append(mapped)
        if mapped != value.strip().lower():
            mappings.append({"input": value.strip().lower(), "normalized": mapped})
    return normalized, mappings


def ensure_artifacts() -> None:
    required = [
        _artifact("label_encoder.joblib"),
        _artifact("retrieval_index.joblib"),
        _artifact("metrics.json"),
    ]
    if all(os.path.exists(p) for p in required):
        with open(_artifact("metrics.json"), "r", encoding="utf-8") as f:
            metrics = json.load(f)
        best_art = metrics.get("best", {}).get("artifact")
        if best_art and os.path.exists(_artifact(best_art)):
            return

    result = subprocess.run([sys.executable, os.path.join(BASE_DIR, "train_models.py")], cwd=BASE_DIR)
    if result.returncode != 0:
        raise RuntimeError("Model training failed")


def load_assets() -> Tuple[Any, Any, Dict[str, Any], Dict[str, Any]]:
    ensure_artifacts()
    label_encoder = joblib.load(_artifact("label_encoder.joblib"))
    retrieval_index = joblib.load(_artifact("retrieval_index.joblib"))
    with open(_artifact("metrics.json"), "r", encoding="utf-8") as f:
        metrics = json.load(f)

    best_artifact = metrics.get("best", {}).get("artifact")
    if not best_artifact:
        raise RuntimeError("Invalid metrics.json: missing best model artifact")
    model = joblib.load(_artifact(best_artifact))
    return model, label_encoder, retrieval_index, metrics


def build_request_frame(ingredients: List[str], preferred_cuisines: List[str] | None = None, diet_preference: str | None = None):
    import pandas as pd

    preferred_cuisines = [str(x).strip().lower() for x in (preferred_cuisines or []) if str(x).strip()]
    diet_values = [str(diet_preference).strip().lower()] if diet_preference and str(diet_preference).strip().lower() != "balanced" else []
    row = {
        "ingredient_text": " ".join(ingredients),
        "metadata_text": " ".join(
            [*(f"cuisine_{x.replace(' ', '_')}" for x in preferred_cuisines), *(f"diet_{x.replace(' ', '_')}" for x in diet_values)]
        ),
        "combined_text": " ".join(
            [
                " ".join(ingredients),
                " ".join([*(f"cuisine_{x.replace(' ', '_')}" for x in preferred_cuisines), *(f"diet_{x.replace(' ', '_')}" for x in diet_values)]),
            ]
        ).strip(),
        "cuisine_list": preferred_cuisines,
        "diet_list": diet_values,
        "dish_type_list": [],
    }
    return pd.DataFrame([row])


def softmax(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    shifted = values - values.max()
    exp = np.exp(shifted)
    return exp / (exp.sum() + 1e-12)


def get_model_scores(model: Any, request_frame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(request_frame))[0]
    if hasattr(model, "decision_function"):
        scores = np.asarray(model.decision_function(request_frame))[0]
        return softmax(scores)
    prediction = model.predict(request_frame)
    out = np.zeros(int(np.max(prediction)) + 1, dtype=float)
    out[int(prediction[0])] = 1.0
    return out


def ingredient_overlap_score(input_ingredients: List[str], recipe_ingredients: List[str]) -> float:
    input_set = set(input_ingredients)
    recipe_set = set(recipe_ingredients)
    if not input_set or not recipe_set:
        return 0.0
    exact_overlap = len(input_set & recipe_set)
    partial_overlap = 0
    for user_ing in input_set:
        for recipe_ing in recipe_set:
            if user_ing == recipe_ing:
                continue
            if user_ing in recipe_ing or recipe_ing in user_ing:
                partial_overlap += 1
                break
    coverage = exact_overlap / len(input_set)
    precision = exact_overlap / len(recipe_set)
    partial_bonus = min(partial_overlap, len(input_set)) / len(input_set) * 0.15
    return (coverage * 0.65) + (precision * 0.20) + partial_bonus


def metadata_match_score(recipe: Dict[str, Any], preferred_cuisines: List[str], diet_preference: str | None) -> float:
    score = 0.0
    recipe_cuisines = set(recipe.get("cuisines") or [])
    if preferred_cuisines:
        preferred = set(preferred_cuisines)
        if recipe_cuisines & preferred:
            score += 0.15
    recipe_diets = set(recipe.get("diets") or [])
    desired_diet = (diet_preference or "").strip().lower()
    if desired_diet and desired_diet != "balanced" and desired_diet in recipe_diets:
        score += 0.15
    return score


def retrieval_rank(
    grouped_scores: np.ndarray,
    label_encoder: Any,
    retrieval_index: Dict[str, Any],
    ingredients: List[str],
    preferred_cuisines: List[str],
    diet_preference: str | None,
    top_k: int,
) -> List[Tuple[str, float, str]]:
    recipes = retrieval_index.get("all_recipes", [])
    group_names = list(label_encoder.classes_)
    ranked: List[Tuple[str, float, str]] = []
    for recipe in recipes:
        group_name = recipe.get("target_group", "misc_recipe")
        if group_name in group_names:
            group_idx = group_names.index(group_name)
            model_score = float(grouped_scores[group_idx]) if group_idx < len(grouped_scores) else 0.0
        else:
            model_score = 0.0
        overlap = ingredient_overlap_score(ingredients, recipe.get("ingredients") or [])
        meta_bonus = metadata_match_score(recipe, preferred_cuisines, diet_preference)
        final_score = (model_score * 0.45) + (overlap * 0.45) + meta_bonus
        ranked.append((recipe.get("recipe", "Unknown"), final_score, group_name))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:top_k]


def find_substitutions(ingredients: List[str]) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    for ingredient in ingredients:
        if ingredient in SUBSTITUTION_MAP:
            suggestions.append(
                {
                    "ingredient": ingredient,
                    "alternatives": SUBSTITUTION_MAP[ingredient],
                    "reason": "Useful if the ingredient is unavailable or needs an allergy-friendly swap.",
                }
            )
    return suggestions


def infer_diet_match(ingredients: List[str], preferred_diet: str | None) -> Dict[str, Any]:
    preferred = (preferred_diet or "balanced").strip().lower() or "balanced"
    restricted = DIET_KEYWORDS.get(preferred, set())
    conflicts = sorted([item for item in ingredients if item in restricted])
    return {
        "diet": preferred,
        "compatible": len(conflicts) == 0,
        "conflicts": conflicts,
    }


def infer_cuisine_tags(recipe_name: str) -> List[str]:
    lower = recipe_name.lower()
    tags = []
    if any(word in lower for word in ["curry", "masala", "paneer", "biryani"]):
        tags.append("indian")
    if any(word in lower for word in ["pasta", "pizza", "risotto"]):
        tags.append("italian")
    if any(word in lower for word in ["taco", "salsa", "quesadilla", "guacamole"]):
        tags.append("mexican")
    if any(word in lower for word in ["noodle", "fried rice", "soy", "jambalaya"]):
        tags.append("asian")
    return tags or ["global"]


def build_personalization_hint(alternatives: List[Tuple[str, float, str]], history_predictions: List[str], preferred_cuisines: List[str]) -> str:
    repeated = [name for name, count in Counter(history_predictions).items() if count >= 2]
    alt_names = [name for name, _, _ in alternatives]
    cuisine_match = [name for name in alt_names if any(c in name.lower() for c in preferred_cuisines)] if preferred_cuisines else []
    if cuisine_match:
        return f"These results loosely align with your cuisine interests: {', '.join(cuisine_match[:2])}."
    if repeated:
        return f"Based on your history, you often explore dishes like {', '.join(repeated[:2])}."
    return "As your history grows, recommendations can be re-ranked more strongly around your recurring tastes."


def predict_from_ingredients(
    ingredients: List[str],
    top_k: int = 5,
    allergy_profile: List[str] | None = None,
    preferred_cuisines: List[str] | None = None,
    diet_preference: str | None = None,
    history_predictions: List[str] | None = None,
) -> Dict[str, Any]:
    model, label_encoder, retrieval_index, metrics = load_assets()
    normalized_ingredients, normalization_map = normalize_ingredients(ingredients)
    filtered = [item for item in normalized_ingredients if item]
    if not filtered:
        return {
            "predicted_recipe": "Unknown",
            "reason": "No known ingredients",
            "normalization_map": normalization_map,
            "substitutions": find_substitutions(normalized_ingredients),
        }

    preferred_cuisines = [str(x).strip().lower() for x in (preferred_cuisines or []) if str(x).strip()]
    request_frame = build_request_frame(filtered, preferred_cuisines=preferred_cuisines, diet_preference=diet_preference)
    grouped_scores = get_model_scores(model, request_frame)
    ranked = retrieval_rank(grouped_scores, label_encoder, retrieval_index, filtered, preferred_cuisines, diet_preference, top_k)
    if not ranked:
        return {
            "predicted_recipe": "Unknown",
            "reason": "No ranked recipes found",
            "normalization_map": normalization_map,
        }

    best_recipe, best_score, best_group = ranked[0]
    substitutions = find_substitutions(normalized_ingredients)
    diet_match = infer_diet_match(filtered, diet_preference)
    history_predictions = history_predictions or []
    allergy_profile = allergy_profile or []
    grouped_top_idx = np.argsort(grouped_scores)[-min(top_k, len(grouped_scores)):][::-1]
    top_groups = [(str(label_encoder.inverse_transform([int(i)])[0]), float(grouped_scores[int(i)])) for i in grouped_top_idx]

    return {
        "predicted_recipe": best_recipe,
        "predicted_group": best_group,
        "confidence": float(best_score),
        "alternatives": [(name, float(score)) for name, score, _ in ranked],
        "top_groups": top_groups,
        "model": metrics.get("best", {}).get("name", "unknown_model"),
        "used_ingredients": filtered,
        "normalization_map": normalization_map,
        "substitutions": substitutions,
        "diet_match": diet_match,
        "cuisine_tags": infer_cuisine_tags(best_recipe),
        "personalization_hint": build_personalization_hint(ranked, history_predictions, preferred_cuisines),
        "allergy_profile": allergy_profile,
        "explanation": "Prediction is generated by a grouped classification model and then re-ranked against actual recipes using ingredient overlap and metadata match.",
        "enhancement": "The improved pipeline uses TF-IDF features, metadata features, grouped targets, cross-validation-trained models, and retrieval-style reranking.",
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No ingredients provided"}))
        sys.exit(1)

    raw = sys.argv[1]
    ingredients = [i.strip().lower() for i in raw.split(",") if i.strip()]
    if not ingredients:
        print(json.dumps({"error": "No ingredients provided"}))
        sys.exit(1)

    try:
        context = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        out = predict_from_ingredients(
            ingredients,
            allergy_profile=context.get("allergyProfile") or [],
            preferred_cuisines=context.get("preferredCuisines") or [],
            diet_preference=context.get("dietPreference") or "balanced",
            history_predictions=context.get("historyPredictions") or [],
        )
        print(json.dumps(out))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()