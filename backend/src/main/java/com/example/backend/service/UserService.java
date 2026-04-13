package com.example.backend.service;

import com.example.backend.model.UserRecord;
import com.example.backend.store.JsonFileStore;
import com.fasterxml.jackson.core.type.TypeReference;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class UserService {
    private static final String USERS_FILE = "users.json";
    private final JsonFileStore store;
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    public UserService(JsonFileStore store) {
        this.store = store;
    }

    public synchronized UserRecord register(String name, String email, String password) {
        List<UserRecord> users = loadUsers();
        String normalizedEmail = email.trim().toLowerCase();
        boolean exists = users.stream().anyMatch(u -> normalizedEmail.equalsIgnoreCase(u.getEmail()));
        if (exists) {
            throw new IllegalArgumentException("Email already registered");
        }
        UserRecord user = new UserRecord();
        user.setId(UUID.randomUUID().toString());
        user.setName(name.trim());
        user.setEmail(normalizedEmail);
        user.setPasswordHash(encoder.encode(password));
        user.setRole("USER");
        user.setCreatedAt(Instant.now());
        user.setAllergyProfile(new ArrayList<>());
        user.setPreferredCuisines(new ArrayList<>());
        user.setDietPreference("balanced");
        users.add(user);
        store.writeList(USERS_FILE, users);
        return user;
    }

    public Optional<UserRecord> authenticate(String email, String password) {
        String normalizedEmail = email.trim().toLowerCase();
        return loadUsers().stream()
                .filter(u -> normalizedEmail.equalsIgnoreCase(u.getEmail()) && encoder.matches(password, u.getPasswordHash()))
                .findFirst();
    }

    public Optional<UserRecord> findById(String id) {
        return loadUsers().stream().filter(u -> u.getId().equals(id)).findFirst();
    }

    public synchronized Optional<UserRecord> updateAiPreferences(String userId, List<String> allergyProfile, List<String> preferredCuisines, String dietPreference) {
        List<UserRecord> users = loadUsers();
        for (UserRecord user : users) {
            if (user.getId().equals(userId)) {
                user.setAllergyProfile(allergyProfile == null ? new ArrayList<>() : new ArrayList<>(allergyProfile));
                user.setPreferredCuisines(preferredCuisines == null ? new ArrayList<>() : new ArrayList<>(preferredCuisines));
                user.setDietPreference(dietPreference == null || dietPreference.isBlank() ? "balanced" : dietPreference.trim().toLowerCase());
                store.writeList(USERS_FILE, users);
                return Optional.of(user);
            }
        }
        return Optional.empty();
    }

    private List<UserRecord> loadUsers() {
        return store.readList(USERS_FILE, new TypeReference<List<UserRecord>>() {});
    }
}