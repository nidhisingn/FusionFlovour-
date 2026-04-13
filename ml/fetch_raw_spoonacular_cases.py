import requests
import csv
import time
import json

API_URL = "https://api.spoonacular.com/recipes/complexSearch"
DETAIL_URL = "https://api.spoonacular.com/recipes/{id}/information"
API_KEY = "7a60de9eade043338c3bab3d530cedd3"
BATCH_SIZE = 50
MAX_RECIPES = 250  # adjust as needed for quota

def fetch_recipes(offset, number=50):
    params = {
        "number": number,
        "offset": offset,
        "apiKey": API_KEY,
    }
    resp = requests.get(API_URL, params=params)
    resp.raise_for_status()
    return resp.json().get('results', [])

def fetch_recipe_details(recipe_id):
    params = {"apiKey": API_KEY}
    url = DETAIL_URL.format(id=recipe_id)
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

def main():
    with open("spoonacular_details_allcases.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        headers_written = False
        for offset in range(0, MAX_RECIPES, BATCH_SIZE):
            try:
                base_recipes = fetch_recipes(offset, BATCH_SIZE)
                if not base_recipes:
                    break
                print(f"Fetched {len(base_recipes)} base recipes at offset {offset}...")
                for base in base_recipes:
                    r_id = base.get('id')
                    title = base.get("title", "").strip()
                    if not title or not r_id:
                        continue
                    try:
                        detail = fetch_recipe_details(r_id)
                        if not headers_written:
                            all_keys = sorted(detail.keys())
                            writer.writerow(["id", "title"] + all_keys)
                            headers_written = True
                        row = [r_id, title] + [json.dumps(detail.get(k, ""), ensure_ascii=False) for k in all_keys]
                        writer.writerow(row)
                    except Exception as e:
                        print(f"Detail fetch failed for ID {r_id}: {e}")
                        continue
                time.sleep(1.2)
            except Exception as e:
                print(f"Error at offset {offset}: {e}")
                break
    print("Done. All raw detail cases saved in spoonacular_details_allcases.csv")

if __name__ == "__main__":
    main()
