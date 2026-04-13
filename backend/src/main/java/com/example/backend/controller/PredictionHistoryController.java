package com.example.backend.controller;

import com.example.backend.security.JwtAuthenticationFilter;
import com.example.backend.security.RequestUser;
import com.example.backend.service.PredictionHistoryService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletRequest;
import java.util.Map;

@RestController
@RequestMapping("/history")
@CrossOrigin(origins = "*")
public class PredictionHistoryController {
    private final PredictionHistoryService predictionHistoryService;

    public PredictionHistoryController(PredictionHistoryService predictionHistoryService) {
        this.predictionHistoryService = predictionHistoryService;
    }

    @GetMapping
    public ResponseEntity<?> history(HttpServletRequest request) {
        RequestUser user = (RequestUser) request.getAttribute(JwtAuthenticationFilter.REQUEST_USER_ATTR);
        if (user == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("error", "Authentication required"));
        }
        return ResponseEntity.ok(predictionHistoryService.forUser(user.getUserId()));
    }
}