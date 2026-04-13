"""Fetch and prepare training data from Spoonacular.

Produces:
  - recipes.csv            -> training file with columns: recipe, ingredients
  - recipes_details_raw.csv -> raw details (debuggable)
  - recipes_base_raw.json   -> raw base results from complexSearch

What we train on (useful fields):
  - recipe title (label)
  - extendedIngredients names (features)

Optionally, we also extract metadata like cuisines/diets/dishTypes which can be
used later to engineer richer features.

NOTE: This script uses your Spoonacular API key. Keep quotas in mind.
"""

import os
import requests
import csv
import time
import json

API_URL = "https://api.spoonacular.com/recipes/complexSearch"
DETAIL_URL = "https://api.spoonacular.com/recipes/{id}/information"

# Prefer env var so key isn't hardcoded.
API_KEY = os.getenv("SPOONACULAR_API_KEY", "7a60de9eade043338c3bab3d530cedd3")

# Spoonacular recommends <= 100 per page for complexSearch.
BATCH_SIZE = 100

# Total recipes to *attempt* (details calls can be less due to filtering).
MAX_RECIPES = 400

# Filters for better dataset quality.
MIN_INGREDIENTS = 3

def fetch_recipes(offset, number=50):
    params = {
        "number": number,
        "offset": offset,
        "apiKey": API_KEY,
        # adding this helps you later if you want cuisine/dishType/diets
        "addRecipeInformation": True,
    }
    resp = requests.get(API_URL, params=params)
    if resp.status_code != 200:
        print(f"[ERROR] fetch_recipes: Status {resp.status_code} {resp.text}")
    resp.raise_for_status()
    return resp.json().get('results', [])

def fetch_recipe_details(recipe_id):
    params = {"apiKey": API_KEY}
    url = DETAIL_URL.format(id=recipe_id)
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"[ERROR] fetch_recipe_details: ID {recipe_id}, Status {resp.status_code} {resp.text}")
    resp.raise_for_status()
    return resp.json()

def extract_ingredients(recipe_detail):
    # get list of ingredient names for a recipe
    ingredients = set()
    for item in recipe_detail.get("extendedIngredients", []):
        # "nameClean" is often normalized; fallback to "name".
        name = item.get("nameClean") or item.get("name")
        if name:
            ingredients.add(name.strip().lower())
    return list(ingredients)


def extract_metadata(recipe_detail):
    """Metadata we may use later for richer features."""
    return {
        "cuisines": recipe_detail.get("cuisines") or [],
        "diets": recipe_detail.get("diets") or [],
        "dishTypes": recipe_detail.get("dishTypes") or [],
        "readyInMinutes": recipe_detail.get("readyInMinutes"),
        "servings": recipe_detail.get("servings"),
        "healthScore": recipe_detail.get("healthScore"),
    }

def main():
    all_rows = []
    seen_titles = set()
    num_detail_errors = 0

    # If today's API quota is over, rely on existing cached CSV if present.
    if os.path.exists("recipes.csv") and os.path.getsize("recipes.csv") > 0:
        print("[INFO] Found existing recipes.csv. If Spoonacular quota is exceeded, we will keep this as fallback.")

    # Raw save files
    with open("recipes_base_raw.json", "w", encoding="utf-8") as raw_base, \
         open("recipes_details_raw.csv", "w", newline='', encoding="utf-8") as raw_details:
        base_obj_list = []
        detail_writer = csv.writer(raw_details)
        detail_writer.writerow(["id", "title", "raw_json"])
        for offset in range(0, MAX_RECIPES, BATCH_SIZE):
            try:
                base_recipes = fetch_recipes(offset, BATCH_SIZE)
                if not base_recipes:
                    break
                base_obj_list.extend(base_recipes)
                print(f"Fetched {len(base_recipes)} base recipes at offset {offset}...")
                for base in base_recipes:
                    r_id = base.get('id')
                    title = base.get("title", "").strip()
                    if not title or title in seen_titles or not r_id:
                        continue
                    try:
                        # If addRecipeInformation=true is used, many fields are already present.
                        # But extendedIngredients are not always present in complexSearch results,
                        # so we still call /information for consistency.
                        detail = fetch_recipe_details(r_id)
                        # save detail as raw text row for debugging
                        detail_writer.writerow([r_id, title, json.dumps(detail, ensure_ascii=False)])
                        ingredients = extract_ingredients(detail)
                        if len(ingredients) >= MIN_INGREDIENTS:
                            meta = extract_metadata(detail)
                            all_rows.append({
                                "recipe": title,
                                "ingredients": "|".join(sorted(ingredients)),
                                # keep meta in the CSV too; train script currently ignores these
                                # but it’s useful for future feature engineering.
                                "cuisines": "|".join([str(x).strip().lower() for x in meta["cuisines"] if str(x).strip()]),
                                "diets": "|".join([str(x).strip().lower() for x in meta["diets"] if str(x).strip()]),
                                "dishTypes": "|".join([str(x).strip().lower() for x in meta["dishTypes"] if str(x).strip()]),
                            })
                            seen_titles.add(title)
                    except Exception as e:
                        print(f"Detail fetch failed for ID {r_id}: {e}")
                        num_detail_errors += 1
                        continue
                time.sleep(1.2)  # avoid API abuse
            except Exception as e:
                print(f"Error at offset {offset}: {e}")
                break
        # Save all collected base objects at the end (one big array)
        raw_base.write(json.dumps(base_obj_list, indent=2, ensure_ascii=False))

    # Write to CSV for ML.
    # If API returned 0 usable rows, do NOT overwrite the existing backup.
    if len(all_rows) == 0:
        print(
            "[WARN] Spoonacular fetch produced 0 usable rows (likely quota exceeded). "
            "Keeping existing recipes.csv as backup."
        )
        return

    # Backup previous recipes.csv (if exists)
    if os.path.exists("recipes.csv") and os.path.getsize("recipes.csv") > 0:
        ts = int(time.time())
        backup_path = f"recipes.backup.{ts}.csv"
        try:
            os.replace("recipes.csv", backup_path)
            print(f"[INFO] Backed up old recipes.csv -> {backup_path}")
        except Exception as e:
            print(f"[WARN] Could not backup old recipes.csv: {e}")

    with open("recipes.csv", "w", newline='', encoding="utf-8") as csvfile:
        fieldnames = ["recipe", "ingredients", "cuisines", "diets", "dishTypes"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)
    print(f"Wrote {len(all_rows)} recipe rows to recipes.csv (and {num_detail_errors} detail errors)")

if __name__ == "__main__":
    main()
