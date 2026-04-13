import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

df = pd.read_csv("recipes.csv")

# Split ingredients to lists
df["ingredient_list"] = df["ingredients"].apply(lambda x: [i.strip().lower() for i in x.split("|")])

# 1. Number of unique recipes and ingredients
print(f"Unique recipes: {df['recipe'].nunique()}")
all_ingredients = [ing for lst in df["ingredient_list"] for ing in lst]
ingredient_counts = Counter(all_ingredients)
print(f"Unique ingredients: {len(ingredient_counts)}")

# 2. Class balance
recipe_counts = df["recipe"].value_counts()
plt.figure(figsize=(10,3))
plt.hist(recipe_counts, bins=20, color='teal')
plt.title("Recipe sample distribution (should all be 1)")
plt.show()

# 3. Top-20 most frequent ingredients
top_20 = ingredient_counts.most_common(20)
plt.figure(figsize=(12,6))
plt.barh([ing for ing, _ in top_20], [cnt for _, cnt in top_20])
plt.xlabel("Frequency")
plt.title("Top 20 Most Frequent Ingredients")
plt.gca().invert_yaxis()
plt.show()

# 4. Number of ingredients per recipe
plt.figure(figsize=(8,4))
plt.hist(df["ingredient_list"].apply(len), bins=range(2, 35), color='plum')
plt.xlabel("# Ingredients per Recipe")
plt.ylabel("Recipes")
plt.title("Ingredient Count Distribution")
plt.show()

# 5. Print example
print("Sample data row:", df.iloc[0])
