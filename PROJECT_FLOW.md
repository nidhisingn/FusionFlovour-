# Project Flow: Ingredients → Dish Prediction (Frontend + Backend + ML)

This document explains:

- How to run the **frontend**, **backend**, and **ML** components
- Full data flow (what calls what)
- Key files and major functions
- Spoonacular APIs used + exact `curl` commands
- Offline / quota-exceeded fallback behavior

---

## 1) What this project does (objective)

User enters **ingredients** in the React UI → backend receives them → backend executes a Python ML predictor → predictor returns the **dish/recipe name** (plus alternatives).

High-level goal:

> Ingredients as input → predicted dishes that can be made from those ingredients.

---

## 2) Repository structure

```
ml-project/
  frontend/        React + TypeScript UI
  backend/         Spring Boot REST API
  ml/              Python scripts: fetch data, train models, predict
```

---

## 3) End-to-end request flow (runtime)

### Step A: Frontend → Backend

File: `frontend/src/App.tsx`

When you click **Predict Recipe**, it calls:

- `POST http://localhost:8080/predict`

Request body:

```json
{ "ingredients": "tomato,cheese,bread" }
```

### Step B: Backend → Python ML

File: `backend/src/main/java/com/example/backend/PredictController.java`

The backend runs a command similar to:

```bash
python3 ../ml/predict.py "tomato,cheese,bread" ../ml/recipes.csv
```

Note: The extra `../ml/recipes.csv` argument is not required by the current Python script, but it does not break anything because `ml/predict.py` uses only the first argument.

### Step C: Python → Model inference

File: `ml/predict.py`

What it does:

1. Loads model artifacts from `ml/artifacts/`
2. Converts input ingredients into a feature vector using the `MultiLabelBinarizer`
3. Predicts dish probabilities and returns:

```json
{
  "predicted_recipe": "...",
  "confidence": 0.12,
  "alternatives": [["dish1", 0.12], ["dish2", 0.10]],
  "model": "...",
  "used_ingredients": ["tomato", "cheese"]
}
```

### Step D: Backend → Frontend response

Backend parses Python JSON and returns:

```json
{ "prediction": "<dish>" }
```

Frontend displays the dish.

---

## 4) ML pipeline flow (offline / training)

### 4.1 Fetch training data from Spoonacular

File: `ml/fetch_and_prepare_data.py`

Major functions:

- `fetch_recipes(offset, number)`
  - Calls Spoonacular `/recipes/complexSearch` to get base results (id, title, etc.)
- `fetch_recipe_details(recipe_id)`
  - Calls Spoonacular `/recipes/{id}/information` to get `extendedIngredients`
- `extract_ingredients(recipe_detail)`
  - Extracts ingredient names from `extendedIngredients` (uses `nameClean` fallback to `name`)
- `extract_metadata(recipe_detail)`
  - Extracts cuisines/diets/dishTypes (saved to CSV for future feature engineering)

Outputs:

- `ml/recipes.csv` (training dataset)
- `ml/recipes_base_raw.json` (raw base results)
- `ml/recipes_details_raw.csv` (raw details per recipe)

#### Offline fallback / backup behavior

Because Spoonacular free quota can be exceeded (402 error), the script is built to be safe:

- If it fetches **0 usable rows**, it **keeps your existing** `ml/recipes.csv` (backup dataset)
- If it fetches new rows, it backs up your old dataset to:
  - `ml/recipes.backup.<timestamp>.csv`

Environment variable:

```bash
export SPOONACULAR_API_KEY="<your_key>"
```

### 4.2 Train 5 models (+ weighted ensemble)

File: `ml/train_models.py`

What it trains (5 models, + optional Keras):

1. `logreg_ovr` – Logistic Regression One-vs-Rest
2. `linear_svc_calibrated_ovr` – LinearSVC One-vs-Rest (rank via `decision_function`)
3. `multinomial_nb` – Multinomial Naive Bayes
4. `random_forest` – RandomForestClassifier
5. `sklearn_mlp` – MLPClassifier
6. `keras_mlp` – Optional deep model if TensorFlow is available

Also computes:

- `accuracy`
- `top-3 accuracy`

And builds a **weighted soft-voting ensemble** ("weightage") over probability-capable models.

Artifacts saved in:

`ml/artifacts/`

- `mlb_ingredients.joblib`
- `label_encoder.joblib`
- `metrics.json`
- best model artifact, e.g. `linear_svc_calibrated_ovr.joblib`

### 4.3 Predict (CLI) and predict (backend)

File: `ml/predict.py`

Major functions:

- `ensure_artifacts()`
  - Ensures `ml/artifacts/` exists; if missing, triggers training
- `load_best_model()`
  - Reads `metrics.json` and loads the best artifact
- `predict_from_ingredients(ingredients)`
  - Builds multi-hot vector and returns predicted dish + alternatives

---

## 5) Spoonacular API calls + curl commands

### A) complexSearch (collect recipe IDs)

This matches the API your fetch script uses:

```bash
curl -s "https://api.spoonacular.com/recipes/complexSearch?number=100&offset=0&addRecipeInformation=true&apiKey=YOUR_KEY" | jq '.results[]'
```

Your tested working curl (also correct):

```bash
curl -s "https://api.spoonacular.com/recipes/complexSearch?number=100&offset=0&apiKey=YOUR_KEY" | jq '.results[]'
```

### B) recipe information (get extendedIngredients)

For each recipe id from complexSearch:

```bash
curl -s "https://api.spoonacular.com/recipes/<RECIPE_ID>/information?apiKey=YOUR_KEY" | jq '.extendedIngredients'
```

### C) App endpoint to fetch cooking steps (new)

Backend endpoint:

```bash
curl -sG "http://localhost:8080/recipe-info" \
  --data-urlencode "title=Easy To Make Spring Rolls" | jq
```

This endpoint internally calls Spoonacular:

1) complexSearch (find id by title)
2) /information (get analyzedInstructions)

---

## 6) How to run everything

### 6.1 One-time (or when you want to refresh dataset)

```bash
export SPOONACULAR_API_KEY="<your_key>"

cd ml
python3 fetch_and_prepare_data.py
python3 train_models.py
```

### 6.2 Start backend

```bash
cd backend
mvn spring-boot:run
```

Backend URL: http://localhost:8080

### 6.3 Start frontend

```bash
cd frontend
npm install
npm start
```

Frontend URL: http://localhost:3000

### 6.4 Use the app

1. Open http://localhost:3000
2. Add ingredients
3. Click **Predict Recipe**
4. It calls backend → python → model → returns prediction.

---

## 7) Notes / limitations (important)

- Spoonacular free tier often hits quota quickly (402). That’s why **backup dataset** is important.
- Model quality depends heavily on dataset size. With very few rows, accuracy will be low.

---

If you want, I can also:

- update backend to remove the unused `csvPath` arg
- add richer features from cuisines/diets/dishTypes into training
- add a top-k results UI in frontend (show alternatives)
