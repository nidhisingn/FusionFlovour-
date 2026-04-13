package com.example.backend.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.time.Instant;
import java.util.Date;
import java.util.Map;

@Service
public class JwtService {
    private Key signingKey;
    private static final long EXPIRY_SECONDS = 60L * 60L * 24L * 7L;

    @PostConstruct
    public void init() {
        String raw = System.getenv().getOrDefault(
                "APP_JWT_SECRET",
                "change-this-dev-secret-key-for-recipe-project-1234567890"
        );
        byte[] keyBytes = raw.getBytes(StandardCharsets.UTF_8);
        if (keyBytes.length < 32) {
            byte[] padded = new byte[32];
            System.arraycopy(keyBytes, 0, padded, 0, Math.min(keyBytes.length, 32));
            keyBytes = padded;
        }
        signingKey = Keys.hmacShaKeyFor(keyBytes);
    }

    public String generateToken(String userId, String email, String role, String name) {
        Instant now = Instant.now();
        return Jwts.builder()
                .setSubject(userId)
                .addClaims(Map.of(
                        "email", email,
                        "role", role,
                        "name", name
                ))
                .setIssuedAt(Date.from(now))
                .setExpiration(Date.from(now.plusSeconds(EXPIRY_SECONDS)))
                .signWith(signingKey, SignatureAlgorithm.HS256)
                .compact();
    }

    public Claims parse(String token) {
        return Jwts.parserBuilder()
                .setSigningKey(signingKey)
                .build()
                .parseClaimsJws(token)
                .getBody();
    }
}