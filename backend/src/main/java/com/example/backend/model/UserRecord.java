package com.example.backend.model;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public class UserRecord {
    private String id;
    private String name;
    private String email;
    private String passwordHash;
    private String role;
    private Instant createdAt;
    private List<String> allergyProfile = new ArrayList<>();
    private List<String> preferredCuisines = new ArrayList<>();
    private String dietPreference;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getPasswordHash() { return passwordHash; }
    public void setPasswordHash(String passwordHash) { this.passwordHash = passwordHash; }
    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public List<String> getAllergyProfile() { return allergyProfile; }
    public void setAllergyProfile(List<String> allergyProfile) { this.allergyProfile = allergyProfile; }
    public List<String> getPreferredCuisines() { return preferredCuisines; }
    public void setPreferredCuisines(List<String> preferredCuisines) { this.preferredCuisines = preferredCuisines; }
    public String getDietPreference() { return dietPreference; }
    public void setDietPreference(String dietPreference) { this.dietPreference = dietPreference; }
}