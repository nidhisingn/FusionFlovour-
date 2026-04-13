package com.example.backend.security;

public class RequestUser {
    private final String userId;
    private final String email;
    private final String role;
    private final String name;

    public RequestUser(String userId, String email, String role, String name) {
        this.userId = userId;
        this.email = email;
        this.role = role;
        this.name = name;
    }

    public String getUserId() { return userId; }
    public String getEmail() { return email; }
    public String getRole() { return role; }
    public String getName() { return name; }
}