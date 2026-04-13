package com.example.backend.controller;

import com.example.backend.model.UserRecord;
import com.example.backend.security.JwtAuthenticationFilter;
import com.example.backend.security.JwtService;
import com.example.backend.security.RequestUser;
import com.example.backend.service.UserService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/auth")
@CrossOrigin(origins = "*")
public class AuthController {
    private final UserService userService;
    private final JwtService jwtService;

    public AuthController(UserService userService, JwtService jwtService) {
        this.userService = userService;
        this.jwtService = jwtService;
    }

    @PostMapping("/signup")
    public ResponseEntity<?> signup(@RequestBody Map<String, String> body) {
        try {
            String name = body.getOrDefault("name", "").trim();
            String email = body.getOrDefault("email", "").trim();
            String password = body.getOrDefault("password", "");
            if (name.isBlank() || email.isBlank() || password.length() < 6) {
                return ResponseEntity.badRequest().body(Map.of("error", "Name, email, and password(min 6) are required"));
            }
            UserRecord user = userService.register(name, email, password);
            return ResponseEntity.status(HttpStatus.CREATED).body(authPayload(user));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> body) {
        String email = body.getOrDefault("email", "").trim();
        String password = body.getOrDefault("password", "");
        return userService.authenticate(email, password)
                .<ResponseEntity<?>>map(user -> ResponseEntity.ok(authPayload(user)))
                .orElseGet(() -> ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("error", "Invalid credentials")));
    }

    @GetMapping("/me")
    public ResponseEntity<?> me(HttpServletRequest request) {
        RequestUser requestUser = (RequestUser) request.getAttribute(JwtAuthenticationFilter.REQUEST_USER_ATTR);
        if (requestUser == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("error", "Unauthorized"));
        }
        return userService.findById(requestUser.getUserId())
                .<ResponseEntity<?>>map(user -> ResponseEntity.ok(safeUser(user)))
                .orElseGet(() -> ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("error", "Unauthorized")));
    }

    @PutMapping("/preferences")
    public ResponseEntity<?> updatePreferences(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        RequestUser requestUser = (RequestUser) request.getAttribute(JwtAuthenticationFilter.REQUEST_USER_ATTR);
        if (requestUser == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("error", "Unauthorized"));
        }

        List<String> allergyProfile = normalizeList(body.get("allergyProfile"));
        List<String> preferredCuisines = normalizeList(body.get("preferredCuisines"));
        String dietPreference = String.valueOf(body.getOrDefault("dietPreference", "balanced"));

        return userService.updateAiPreferences(requestUser.getUserId(), allergyProfile, preferredCuisines, dietPreference)
                .<ResponseEntity<?>>map(user -> ResponseEntity.ok(Map.of(
                        "message", "Preferences updated",
                        "user", safeUser(user)
                )))
                .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", "User not found")));
    }

    private Map<String, Object> authPayload(UserRecord user) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("token", jwtService.generateToken(user.getId(), user.getEmail(), user.getRole(), user.getName()));
        data.put("user", safeUser(user));
        return data;
    }

    private Map<String, Object> safeUser(UserRecord user) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", user.getId());
        out.put("name", user.getName());
        out.put("email", user.getEmail());
        out.put("role", user.getRole());
        out.put("createdAt", user.getCreatedAt());
        out.put("allergyProfile", user.getAllergyProfile() == null ? List.of() : user.getAllergyProfile());
        out.put("preferredCuisines", user.getPreferredCuisines() == null ? List.of() : user.getPreferredCuisines());
        out.put("dietPreference", user.getDietPreference() == null ? "balanced" : user.getDietPreference());
        return out;
    }

    private List<String> normalizeList(Object raw) {
        if (raw == null) return new ArrayList<>();
        if (raw instanceof List<?>) {
            return ((List<?>) raw).stream()
                    .map(String::valueOf)
                    .map(String::trim)
                    .map(String::toLowerCase)
                    .filter(s -> !s.isBlank())
                    .distinct()
                    .collect(Collectors.toList());
        }
        return Arrays.stream(String.valueOf(raw).split(","))
                .map(String::trim)
                .map(String::toLowerCase)
                .filter(s -> !s.isBlank())
                .distinct()
                .collect(Collectors.toList());
    }
}