package com.example.backend.security;

import io.jsonwebtoken.Claims;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {
    public static final String REQUEST_USER_ATTR = "requestUser";

    private final JwtService jwtService;

    public JwtAuthenticationFilter(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            String token = header.substring(7).trim();
            try {
                Claims claims = jwtService.parse(token);
                RequestUser requestUser = new RequestUser(
                        claims.getSubject(),
                        String.valueOf(claims.get("email")),
                        String.valueOf(claims.get("role")),
                        String.valueOf(claims.get("name"))
                );
                request.setAttribute(REQUEST_USER_ATTR, requestUser);
            } catch (Exception ignored) {
            }
        }
        filterChain.doFilter(request, response);
    }
}