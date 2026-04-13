package com.example.backend.service;

import com.example.backend.model.PredictionHistoryRecord;
import com.example.backend.store.JsonFileStore;
import com.fasterxml.jackson.core.type.TypeReference;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class PredictionHistoryService {
    private static final String HISTORY_FILE = "prediction_history.json";
    private final JsonFileStore store;

    public PredictionHistoryService(JsonFileStore store) {
        this.store = store;
    }

    public synchronized void save(String userId, List<String> ingredients, String prediction, List<String> alternatives) {
        List<PredictionHistoryRecord> all = loadAll();
        PredictionHistoryRecord row = new PredictionHistoryRecord();
        row.setId(UUID.randomUUID().toString());
        row.setUserId(userId);
        row.setIngredients(ingredients);
        row.setPrediction(prediction);
        row.setAlternatives(alternatives);
        row.setCreatedAt(Instant.now());
        all.add(row);
        store.writeList(HISTORY_FILE, all);
    }

    public List<PredictionHistoryRecord> forUser(String userId) {
        return loadAll().stream()
                .filter(r -> userId.equals(r.getUserId()))
                .sorted(Comparator.comparing(PredictionHistoryRecord::getCreatedAt).reversed())
                .limit(10)
                .collect(Collectors.toList());
    }

    private List<PredictionHistoryRecord> loadAll() {
        return store.readList(HISTORY_FILE, new TypeReference<List<PredictionHistoryRecord>>() {});
    }
}