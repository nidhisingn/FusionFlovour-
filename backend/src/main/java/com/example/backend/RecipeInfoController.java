package com.example.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Fetches cooking instructions / recipe URL from Spoonacular for a given recipe title.
 *
 * Endpoint:
 *   GET /recipe-info?title=<recipe title>
 *
 * Behavior:
 * - Uses Spoonacular complexSearch to find a recipe ID by title.
 * - Then calls /recipes/{id}/information to get summary/sourceUrl/analyzedInstructions.
 * - Caches results in-memory so repeated calls don't consume extra points.
 */
@RestController
@CrossOrigin(origins = "*")
public class RecipeInfoController {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String API_KEY = System.getenv().getOrDefault(
            "SPOONACULAR_API_KEY",
            "7a60de9eade043338c3bab3d530cedd3"
    );

    private static final String SEARCH_URL = "https://api.spoonacular.com/recipes/complexSearch";
    private static final String INFO_URL = "https://api.spoonacular.com/recipes/%s/information";

    // Simple in-memory cache: title -> response
    private static final Map<String, Map<String, Object>> CACHE = new ConcurrentHashMap<>();

    @GetMapping(value = "/recipe-info", produces = "application/json")
    public ResponseEntity<Map<String, Object>> recipeInfo(@RequestParam("title") String title) {
        try {
            if (title == null || title.trim().isEmpty()) {
                return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                        .body(Map.of("error", "Missing title"));
            }

            String normalized = title.trim().toLowerCase(Locale.ROOT);
            if (CACHE.containsKey(normalized)) {
                return ResponseEntity.ok(CACHE.get(normalized));
            }

            // 1) Find a recipe id by title
            Integer recipeId = findRecipeIdByTitle(title.trim());
            if (recipeId == null) {
                return ResponseEntity.status(HttpStatus.NOT_FOUND)
                        .body(Map.of("error", "Recipe not found on Spoonacular", "title", title));
            }

            // 2) Fetch details + instructions
            Map<String, Object> info = fetchRecipeInformation(recipeId);
            info.put("title", title);
            info.put("id", recipeId);

            CACHE.put(normalized, info);
            return ResponseEntity.ok(info);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Server error: " + e.getMessage()));
        }
    }

    private Integer findRecipeIdByTitle(String title) throws Exception {
        String url = SEARCH_URL
                + "?number=1"
                + "&query=" + URLEncoder.encode(title, StandardCharsets.UTF_8)
                + "&apiKey=" + URLEncoder.encode(API_KEY, StandardCharsets.UTF_8);
        JsonNode root = httpGetJson(url);
        JsonNode results = root.get("results");
        if (results == null || !results.isArray() || results.size() == 0) {
            return null;
        }
        JsonNode first = results.get(0);
        if (first == null || first.get("id") == null) {
            return null;
        }
        return first.get("id").asInt();
    }

    private Map<String, Object> fetchRecipeInformation(int id) throws Exception {
        String url = String.format(INFO_URL, id)
                + "?apiKey=" + URLEncoder.encode(API_KEY, StandardCharsets.UTF_8)
                + "&includeNutrition=false";
        JsonNode root = httpGetJson(url);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("sourceUrl", root.path("sourceUrl").asText(""));
        out.put("spoonacularSourceUrl", root.path("spoonacularSourceUrl").asText(""));
        out.put("summary", root.path("summary").asText(""));

        // analyzedInstructions: array -> steps
        List<String> steps = new ArrayList<>();
        JsonNode instructions = root.get("analyzedInstructions");
        if (instructions != null && instructions.isArray()) {
            for (JsonNode inst : instructions) {
                JsonNode instSteps = inst.get("steps");
                if (instSteps != null && instSteps.isArray()) {
                    for (JsonNode s : instSteps) {
                        String step = s.path("step").asText("");
                        if (!step.isBlank()) {
                            steps.add(step);
                        }
                    }
                }
            }
        }
        out.put("steps", steps);
        return out;
    }

    private JsonNode httpGetJson(String urlStr) throws Exception {
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(20000);

        int status = conn.getResponseCode();
        BufferedReader br;
        if (status >= 200 && status < 300) {
            br = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
        } else {
            br = new BufferedReader(new InputStreamReader(conn.getErrorStream(), StandardCharsets.UTF_8));
        }
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) {
            sb.append(line);
        }
        br.close();

        if (status < 200 || status >= 300) {
            throw new RuntimeException("Spoonacular error (" + status + "): " + sb);
        }

        return MAPPER.readTree(sb.toString());
    }
}
