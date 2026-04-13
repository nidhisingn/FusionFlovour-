# Detailed Project Explanation (Frontend + Backend + ML)

This file is a deeper explanation of **how your project works**, why each part exists, and what happens at runtime.

If you want a shorter checklist-style guide, see: `PROJECT_FLOW.md`.

---

## 1) Problem statement

Input: a list of ingredients (e.g., `tomato, cheese, bread`).

Output: a dish/recipe name that can likely be made with those ingredients.

This is treated as a **multi-class classification** problem:

- **X (features)**: ingredients for a recipe
- **y (label)**: the recipe/dish name

---

## 2) System architecture overview

There are 3 layers:

1. **Frontend (React)** – collects ingredients from the user.
2. **Backend (Spring Boot)** – REST API and orchestration layer.
3. **ML (Python)** – training + prediction.

---

## 3) Frontend (React)

### Main file

- `frontend/src/App.tsx`

### What it does

- Takes ingredient input as chips (one by one)
- On submit, sends a request:

```http
POST http://localhost:8080/predict
Content-Type: application/json

{ "ingredients": "tomato,cheese,bread" }
```

### What it displays

- The returned predicted recipe (`data.prediction`) or an error.

---

## 4) Backend (Spring Boot)

### Main file

- `backend/src/main/java/com/example/backend/PredictController.java`

### What it does

- Exposes endpoint: `POST /predict`
- Reads ingredients from JSON body
- Executes Python:

```bash
python3 ../ml/predict.py "<ingredients>" ../ml/recipes.csv
```

Then parses the JSON printed by Python and returns:

```json
{ "prediction": "<predicted_recipe>" }
```

### Why backend calls Python (instead of ML server)

Right now the integration approach is:

- Spring Boot spawns a python process per request

Pros:

- Simple for a project / prototype
- No separate ML server to deploy

Cons:

- Slightly slower per request (starts python process)
- Harder to scale

If you want later, we can convert ML to a **FastAPI** microservice.

---

## 5) ML layer (Python)

There are 3 major responsibilities:

1. **Fetch & build dataset** (Spoonacular → `recipes.csv`)
2. **Train models** (dataset → `ml/artifacts/*`)
3. **Predict** (ingredients → predicted dish)

---

## 6) Dataset creation (Spoonacular)

### File

- `ml/fetch_and_prepare_data.py`

### APIs used

1) **complexSearch** to get recipe ids + titles:

```bash
curl -s "https://api.spoonacular.com/recipes/complexSearch?number=100&offset=0&addRecipeInformation=true&apiKey=YOUR_KEY" | jq '.results[]'
```

2) **information** to get ingredients (`extendedIngredients`) for each recipe id:

```bash
curl -s "https://api.spoonacular.com/recipes/<RECIPE_ID>/information?apiKey=YOUR_KEY" | jq '.extendedIngredients'
```

### What fields we use for training

- **Label (y):** recipe title
- **Features (X):** ingredient names from `extendedIngredients` (normalized)

We also store these extra columns in the CSV for future improvement:

- cuisines
- diets
- dishTypes

### Backup/fallback when free quota is exceeded

Spoonacular free quota often returns 402 once daily points are over.

So the script is designed to be safe:

- If it cannot fetch any usable rows today, it **keeps your existing** `recipes.csv`.
- If it successfully fetches new rows, it backs up the old file:

`recipes.backup.<timestamp>.csv`

This means your app still works offline using the cached CSV.

---

## 7) Training (5 models + weighted ensemble)

### File

- `ml/train_models.py`

### How features are built

We convert ingredient lists into a **multi-hot vector**:

- Each ingredient becomes a feature column.
- If the ingredient exists in recipe, column = 1 else 0.

This is implemented using:

- `MultiLabelBinarizer`

### Models trained (5 required + optional 6th)

This project trains multiple models to satisfy your "train with 5 models" requirement:

1. Logistic Regression (OvR)
2. LinearSVC (OvR)
3. Multinomial Naive Bayes
4. Random Forest
5. sklearn MLP
6. Optional Keras MLP (TensorFlow)

### “Weightage” / ensemble logic

We also create a **soft-voting ensemble** (weighted average of probabilities) where:

- models with better top-3 accuracy get higher weight.

### Artifacts saved

All trained objects are saved to:

`ml/artifacts/`

So prediction does NOT need to retrain repeatedly.

---

## 8) Prediction (`ml/predict.py`) — does it retrain on every request?

### Key answer

No — it **does not** retrain on every request.

Think of it like this:

- **Training** creates and saves model files (artifacts) on disk.
- **Prediction** loads those files and runs inference.

Once trained, the model is stored as files in `ml/artifacts/`. Those files stay there even if you stop the backend or restart your laptop.

### What happens on each backend request?

When backend hits Python predictor:

1) Python checks whether model artifacts exist in `ml/artifacts/`
2) If they exist → it loads them and predicts immediately
3) If they do NOT exist (first run / deleted) → it triggers `train_models.py` once

So training happens only in these cases:

- first time ever
- artifacts deleted
- you intentionally retrain

### Do you need an ML server running all the time?

No.

Current design:

- Backend starts a python process for each request
- Python loads model artifacts from disk and predicts

So:

- You need **backend** running
- You need **frontend** running
- You do **not** run a separate "ML server"

### Important clarification: “ML server down” vs “python not running”

In *your current design* there is **no separate ML server**.

Python runs only when the backend executes it.

So the correct mental model is:

1. Backend is running (Spring Boot)
2. A request hits `/predict`
3. Backend starts a **new Python process** (it is short-lived)
4. Python loads the trained model from disk and returns the prediction
5. Python process exits

That means:

- There is no always-on python service you need to keep running.
- The model is not "running"; it is a **saved file**.

### What happens if you stop everything and start again tomorrow?

Case A: `ml/artifacts/` is still present

- ✅ Backend will call python
- ✅ Python will **load existing artifacts**
- ✅ Prediction works immediately
- ✅ No retraining happens

Case B: `ml/artifacts/` was deleted / missing

- Backend will call python
- Python will NOT find artifacts
- Python will run training once (`train_models.py`)
- After training completes, prediction can run

Case C: Spoonacular API quota is over

- It does not affect prediction (prediction uses `ml/artifacts/`)
- It only affects data refresh (`fetch_and_prepare_data.py`)
- Your backup `recipes.csv` remains available

### Do we train “again and again” after every restart?

No.

Restarting backend/frontend does NOT delete `ml/artifacts/`.

So normally you train once, and then for many days you just keep predicting using the saved model.

---

## 9) How to run (recommended)

### First-time setup (recommended)

```bash
export SPOONACULAR_API_KEY="<your_key>"

cd ml
python3 fetch_and_prepare_data.py
python3 train_models.py
```

### Normal daily usage

Just start frontend + backend:

```bash
cd backend
mvn spring-boot:run
```

```bash
cd frontend
npm start
```

---
 