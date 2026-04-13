package com.example.backend;

import com.example.backend.model.ArticleRecord;
import com.example.backend.model.UserRecord;
import com.example.backend.security.JwtAuthenticationFilter;
import com.example.backend.security.RequestUser;
import com.example.backend.service.ArticleService;
import com.example.backend.service.PredictionHistoryService;
import com.example.backend.service.UserService;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.http.MediaType;
import org.springframework.http.HttpStatus;

import javax.servlet.http.HttpServletRequest;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.concurrent.TimeUnit;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@RestController
@CrossOrigin(origins = "*")
public class PredictController {

    private static final long PYTHON_TIMEOUT_SECONDS = 25;

    private static final Map<String, List<String>> ALLERGEN_KEYWORDS = createAllergenKeywords();

    private static final Map<String, List<String>> DISH_ALLERGEN_HINTS = createDishAllergenHints();

    private final ArticleService articleService;
    private final PredictionHistoryService predictionHistoryService;
    private final UserService userService;

    public PredictController(ArticleService articleService, PredictionHistoryService predictionHistoryService, UserService userService) {
        this.articleService = articleService;
        this.predictionHistoryService = predictionHistoryService;
        this.userService = userService;
    }

    @PostMapping(value = "/predict", produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Map<String, Object>> predict(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        try {
            String ingredients = (String) body.get("ingredients");
            if (ingredients == null || ingredients.isEmpty()) {
                Map<String, Object> resp = new HashMap<>();
                resp.put("error", "No ingredients provided");
                return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(resp);
            }
            // Command to call python script, passing CSV path and ingredients string
            // Find absolute path to recipes.csv (assuming relative to backend working dir)
            RequestUser requestUser = (RequestUser) request.getAttribute(JwtAuthenticationFilter.REQUEST_USER_ATTR);
            UserRecord currentUser = requestUser == null ? null : userService.findById(requestUser.getUserId()).orElse(null);
            List<String> historyPredictions = requestUser == null ? List.of() : predictionHistoryService.forUser(requestUser.getUserId())
                    .stream()
                    .map(r -> r.getPrediction())
                    .filter(v -> v != null && !v.isBlank())
                    .collect(Collectors.toList());

            Map<String, Object> mlContext = new LinkedHashMap<>();
            mlContext.put("allergyProfile", currentUser == null || currentUser.getAllergyProfile() == null ? List.of() : currentUser.getAllergyProfile());
            mlContext.put("preferredCuisines", currentUser == null || currentUser.getPreferredCuisines() == null ? List.of() : currentUser.getPreferredCuisines());
            mlContext.put("dietPreference", currentUser == null || currentUser.getDietPreference() == null ? "balanced" : currentUser.getDietPreference());
            mlContext.put("historyPredictions", historyPredictions);

            String scriptPath = new java.io.File("ml/predict.py").exists()
                    ? "ml/predict.py"
                    : "../ml/predict.py";

            ProcessBuilder pb = new ProcessBuilder(
                "python3", scriptPath, ingredients,
                new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(mlContext)
            );
            pb.redirectErrorStream(true);
            Process process = pb.start();
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            StringBuilder output = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line);
            }
            boolean finished = process.waitFor(PYTHON_TIMEOUT_SECONDS, TimeUnit.SECONDS);
            if (!finished) {
                process.destroyForcibly();
                Map<String, Object> timeoutResp = new HashMap<>();
                timeoutResp.put("error", "Prediction timed out. Please try again.");
                return ResponseEntity.status(HttpStatus.REQUEST_TIMEOUT).body(timeoutResp);
            }
            int exitCode = process.exitValue();
            // Parse the python output as JSON
            String jsonStr = output.toString();
            Map<String, Object> resp = new HashMap<>();
            try {
                // Try to parse as JSON map
                com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
                Map parsed = mapper.readValue(jsonStr, Map.class);
                if (exitCode != 0 && !parsed.containsKey("predicted_recipe")) {
                    resp.put("error", parsed.getOrDefault("error", "Prediction process failed"));
                    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(resp);
                }
                if (parsed.containsKey("error")) {
                    resp.put("error", parsed.get("error"));
                    return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(resp);
                } else if (parsed.containsKey("predicted_recipe")) {
                    String predictedRecipe = String.valueOf(parsed.get("predicted_recipe"));
                    List<String> ingredientList = splitIngredients(ingredients);
                    List<String> alternativeNames = extractAlternativeNames(parsed.get("alternatives"));
                    List<ArticleRecord> relatedArticles = articleService.findRelated(predictedRecipe, alternativeNames, 5);
                    List<Map<String, Object>> allergyInsights = buildAllergyInsights(ingredientList, predictedRecipe, alternativeNames);

                    resp.put("prediction", predictedRecipe);
                    if (parsed.containsKey("confidence")) resp.put("confidence", parsed.get("confidence"));
                    if (parsed.containsKey("alternatives")) resp.put("alternatives", parsed.get("alternatives"));
                    if (parsed.containsKey("model")) resp.put("model", parsed.get("model"));
                    if (parsed.containsKey("used_ingredients")) resp.put("usedIngredients", parsed.get("used_ingredients"));
                    if (parsed.containsKey("normalization_map")) resp.put("normalizationMap", parsed.get("normalization_map"));
                    if (parsed.containsKey("substitutions")) resp.put("substitutions", parsed.get("substitutions"));
                    if (parsed.containsKey("diet_match")) resp.put("dietMatch", parsed.get("diet_match"));
                    if (parsed.containsKey("cuisine_tags")) resp.put("cuisineTags", parsed.get("cuisine_tags"));
                    if (parsed.containsKey("personalization_hint")) resp.put("personalizationHint", parsed.get("personalization_hint"));
                    if (parsed.containsKey("explanation")) resp.put("explanation", parsed.get("explanation"));
                    if (currentUser != null) resp.put("userPreferences", buildPreferenceSummary(currentUser));
                    resp.put("relatedArticles", relatedArticles);
                    resp.put("allergyInsights", mergeProfileAwareAllergyInsights(allergyInsights, currentUser));

                    if (requestUser != null) {
                        predictionHistoryService.save(requestUser.getUserId(), ingredientList, predictedRecipe, alternativeNames);
                    }
                    return ResponseEntity.ok(resp);
                } else {
                    resp.put("error", "Unexpected Python output: " + jsonStr);
                    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(resp);
                }
            } catch (Exception parseErr) {
                resp.put("error", "Invalid output from Python: " + jsonStr);
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(resp);
            }
        } catch (Exception e) {
            Map<String, Object> resp = new HashMap<>();
            resp.put("error", "Server error: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(resp);
        }
    }

    private List<String> splitIngredients(String ingredients) {
        List<String> out = new ArrayList<>();
        for (String part : ingredients.split(",")) {
            String item = part.trim().toLowerCase();
            if (!item.isEmpty()) {
                out.add(item);
            }
        }
        return out;
    }

    private List<String> extractAlternativeNames(Object alternativesRaw) {
        List<String> names = new ArrayList<>();
        if (!(alternativesRaw instanceof List<?>)) {
            return names;
        }
        List<?> list = (List<?>) alternativesRaw;
        for (Object row : list) {
            if (row instanceof List<?>) {
                List<?> tuple = (List<?>) row;
                if (!tuple.isEmpty()) {
                    names.add(String.valueOf(tuple.get(0)));
                }
            }
        }
        return names;
    }

    private List<Map<String, Object>> buildAllergyInsights(List<String> ingredients, String predictedRecipe, List<String> alternatives) {
        Set<String> matchedAllergens = detectAllergens(ingredients, predictedRecipe, alternatives);
        List<Map<String, Object>> insights = new ArrayList<>();
        if (matchedAllergens.isEmpty()) {
            Map<String, Object> safeInfo = new LinkedHashMap<>();
            safeInfo.put("allergen", "general");
            safeInfo.put("severity", "low");
            safeInfo.put("matchedIngredients", new ArrayList<String>());
            safeInfo.put("message", "No common allergen keywords were detected in the provided ingredients. Please still verify the final recipe ingredients before serving.");
            safeInfo.put("recommendation", "Next you can add a user allergy profile and automatically re-rank recipe predictions to safer dishes.");
            insights.add(safeInfo);
            return insights;
        }

        for (String allergen : matchedAllergens) {
            Map<String, Object> insight = new LinkedHashMap<>();
            List<String> matchedIngredients = findMatchingTerms(ingredients, allergen);
            boolean predictedDishRisk = hasDishRisk(predictedRecipe, allergen);
            List<String> saferAlternatives = findSaferAlternatives(alternatives, allergen);

            insight.put("allergen", allergen);
            insight.put("severity", predictedDishRisk ? "high" : "medium");
            insight.put("matchedIngredients", matchedIngredients);
            insight.put("message", buildAllergyMessage(allergen, predictedRecipe, predictedDishRisk, matchedIngredients));
            insight.put("recommendation", buildRecommendation(allergen, saferAlternatives, predictedDishRisk));
            insight.put("saferAlternatives", saferAlternatives);
            insights.add(insight);
        }

        return insights;
    }

    private List<Map<String, Object>> mergeProfileAwareAllergyInsights(List<Map<String, Object>> baseInsights, UserRecord user) {
        if (user == null || user.getAllergyProfile() == null || user.getAllergyProfile().isEmpty()) {
            return baseInsights;
        }
        List<Map<String, Object>> merged = new ArrayList<>(baseInsights);
        for (String allergy : user.getAllergyProfile()) {
            boolean exists = merged.stream().anyMatch(item -> allergy.equals(String.valueOf(item.get("allergen"))));
            if (!exists) {
                Map<String, Object> info = new LinkedHashMap<>();
                info.put("allergen", allergy);
                info.put("severity", "medium");
                info.put("matchedIngredients", List.of());
                info.put("message", "Saved user allergy preference detected for " + allergy + ". Results should be reviewed with extra care.");
                info.put("recommendation", "Safer alternatives can be prioritized for this allergy profile.");
                info.put("saferAlternatives", List.of());
                merged.add(info);
            }
        }
        return merged;
    }

    private Map<String, Object> buildPreferenceSummary(UserRecord user) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("allergyProfile", user.getAllergyProfile() == null ? List.of() : user.getAllergyProfile());
        out.put("preferredCuisines", user.getPreferredCuisines() == null ? List.of() : user.getPreferredCuisines());
        out.put("dietPreference", user.getDietPreference() == null ? "balanced" : user.getDietPreference());
        return out;
    }

    private Set<String> detectAllergens(List<String> ingredients, String predictedRecipe, List<String> alternatives) {
        Set<String> matched = new LinkedHashSet<>();
        for (String allergen : ALLERGEN_KEYWORDS.keySet()) {
            if (!findMatchingTerms(ingredients, allergen).isEmpty()) {
                matched.add(allergen);
                continue;
            }
            if (hasDishRisk(predictedRecipe, allergen)) {
                matched.add(allergen);
                continue;
            }
            for (String alternative : alternatives) {
                if (hasDishRisk(alternative, allergen)) {
                    matched.add(allergen);
                    break;
                }
            }
        }
        return matched;
    }

    private List<String> findMatchingTerms(List<String> ingredients, String allergen) {
        List<String> terms = ALLERGEN_KEYWORDS.getOrDefault(allergen, List.of());
        Set<String> matches = new LinkedHashSet<>();
        for (String ingredient : ingredients) {
            String normalized = ingredient.toLowerCase(Locale.ROOT);
            for (String term : terms) {
                if (normalized.contains(term)) {
                    matches.add(ingredient);
                }
            }
        }
        return new ArrayList<>(matches);
    }

    private boolean hasDishRisk(String dishName, String allergen) {
        String normalizedDish = dishName == null ? "" : dishName.toLowerCase(Locale.ROOT);
        for (String keyword : DISH_ALLERGEN_HINTS.getOrDefault(allergen, List.of())) {
            if (normalizedDish.contains(keyword)) {
                return true;
            }
        }
        return false;
    }

    private List<String> findSaferAlternatives(List<String> alternatives, String allergen) {
        List<String> safer = new ArrayList<>();
        for (String alternative : alternatives) {
            if (!hasDishRisk(alternative, allergen)) {
                safer.add(alternative);
            }
            if (safer.size() == 3) {
                break;
            }
        }
        return safer;
    }

    private String buildAllergyMessage(String allergen, String predictedRecipe, boolean predictedDishRisk, List<String> matchedIngredients) {
        String ingredientPart = matchedIngredients.isEmpty()
                ? "No direct ingredient keyword matched, but the predicted dish pattern suggests possible exposure."
                : "Matched ingredient(s): " + String.join(", ", matchedIngredients) + ".";
        String dishPart = predictedDishRisk
                ? " The predicted dish '" + predictedRecipe + "' may commonly contain " + allergen + "."
                : " The predicted dish may be okay, but cross-check ingredients carefully.";
        return ingredientPart + dishPart;
    }

    private String buildRecommendation(String allergen, List<String> saferAlternatives, boolean predictedDishRisk) {
        if (!saferAlternatives.isEmpty()) {
            return "If the user has a " + allergen + " allergy, consider safer options like: " + String.join(", ", saferAlternatives) + ".";
        }
        if (predictedDishRisk) {
            return "Recommendation: avoid the current dish for " + allergen + " sensitive users unless you replace the triggering ingredients with allergy-safe substitutes.";
        }
        return "Recommendation: verify labels, prevent cross-contact, and consider adding an allergy-aware re-ranking system for personalized predictions.";
    }

    private static Map<String, List<String>> createAllergenKeywords() {
        Map<String, List<String>> map = new LinkedHashMap<>();
        map.put("dairy", Arrays.asList("milk", "cheese", "butter", "cream", "paneer", "yogurt", "curd", "ghee"));
        map.put("gluten", Arrays.asList("wheat", "bread", "flour", "pasta", "noodle", "soy sauce", "bun"));
        map.put("nuts", Arrays.asList("almond", "cashew", "peanut", "walnut", "pistachio", "hazelnut", "nut"));
        map.put("egg", Arrays.asList("egg", "mayonnaise"));
        map.put("shellfish", Arrays.asList("shrimp", "prawn", "crab", "lobster", "shellfish"));
        map.put("soy", Arrays.asList("soy", "tofu", "edamame"));
        return map;
    }

    private static Map<String, List<String>> createDishAllergenHints() {
        Map<String, List<String>> map = new LinkedHashMap<>();
        map.put("dairy", Arrays.asList("pizza", "alfredo", "paneer", "cheese", "cream", "butter"));
        map.put("gluten", Arrays.asList("pizza", "burger", "pasta", "sandwich", "bread", "noodle"));
        map.put("nuts", Arrays.asList("satay", "baklava", "pesto"));
        map.put("egg", Arrays.asList("omelette", "mayo", "cake"));
        map.put("shellfish", Arrays.asList("shrimp", "prawn", "crab", "lobster"));
        map.put("soy", Arrays.asList("tofu", "teriyaki", "soy"));
        return map;
    }
}
