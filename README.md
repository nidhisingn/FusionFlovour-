# Full Stack Recipe Predictor Scaffold (No-DB MVP)

## Structure

```
ml-project/
  frontend/        # React + TypeScript frontend (user inputs ingredients)
  backend/         # Spring Boot backend (receives ingredients, runs ML python, auth/articles/history)
  ml/              #Python ML and sample recipes dataset (CSV)
```

## New MVP features added

- JWT-based signup/login without MySQL
- File-based JSON persistence for users, articles, and prediction history
- Local image upload for recipe/blog articles
- Prediction response enriched with related recipe articles/blogs
- Logged-in user prediction history endpoint and UI

### Where data is stored

This MVP intentionally does **not** use a database.

- Users: `backend/data/users.json`
- Articles: `backend/data/articles.json`
- Prediction history: `backend/data/prediction_history.json`
- Uploaded images: `backend/data/uploads/`

This is suitable for demo/prototype use. For production, migrate these to MySQL/PostgreSQL/object storage.

## Quickstart

### 1. Start the Python ML environment

Ensure you have Python 3.x installed. The default script is `ml/predict.py` and sample data is in `ml/recipes.csv`.

Test locally:
```sh
cd ml
python3 predict.py "tomato,cheese,bread"
# Output: {"predicted_recipe": "Pizza"}
```

### 2. Start the backend

Ensure JDK 11+ and Maven installed.

Optional environment variables:

```sh
export APP_JWT_SECRET="your-long-secret-key"
export SPOONACULAR_API_KEY="your_spoonacular_key"
```

```sh
cd backend
./mvnw spring-boot:run
# If ./mvnw is not present:
mvn spring-boot:run
```
Backend will run on [http://localhost:8080](http://localhost:8080)

### 3. Start the frontend

```sh
cd frontend
npm start
```
Frontend runs on [http://localhost:3000](http://localhost:3000)

### 4. Using the app

1. Go to [http://localhost:3000](http://localhost:3000) in your browser.
2. Use the **Auth** tab to sign up or log in.
3. Use the **Articles** tab to publish recipe blogs/articles and upload recipe images.
4. Use the **Predict** tab to enter ingredients and get prediction + related recipe articles.
5. Use the **History** tab to see saved predictions for the logged-in user.

## Data flow

```
[Frontend (React)] --POST /predict--> [Backend (Spring Boot)] --calls--> [Python predict.py] --reads--> [recipes.csv]
[Frontend (React)] --POST /auth/signup|login--> [Backend JSON file store]
[Frontend (React)] --POST /articles multipart--> [Backend uploads image + saves article JSON]
[Backend /predict] --matches--> [related local articles/blogs]
```

## Important limitations of this MVP

- No MySQL or external database
- Data is local to one machine/server instance
- If local files are deleted, users/articles/history are lost
- Local image storage is not cloud/object storage
- Best for prototype, student project, or low-scale demo

## Customization

- Add/modify recipes in `ml/recipes.csv`
- Put your ML, data cleaning, or feature extraction in `ml/predict.py`
- Extend backend endpoints for more complex flows or error handling
- Enhance React UI to your use case

---

*Ready for extension or productionization as needed.*
