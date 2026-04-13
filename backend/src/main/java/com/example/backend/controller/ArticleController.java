package com.example.backend.controller;

import com.example.backend.security.JwtAuthenticationFilter;
import com.example.backend.security.RequestUser;
import com.example.backend.service.ArticleService;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import javax.servlet.http.HttpServletRequest;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/articles")
@CrossOrigin(origins = "*")
public class ArticleController {
    private final ArticleService articleService;

    public ArticleController(ArticleService articleService) {
        this.articleService = articleService;
    }

    @GetMapping
    public List<?> listArticles() {
        return articleService.listAll();
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> createArticle(
            HttpServletRequest request,
            @RequestParam("recipeTitle") String recipeTitle,
            @RequestParam("title") String title,
            @RequestParam("content") String content,
            @RequestParam(value = "summary", required = false) String summary,
            @RequestParam(value = "tags", required = false) String tags,
            @RequestPart(value = "image", required = false) MultipartFile image
    ) {
        RequestUser user = (RequestUser) request.getAttribute(JwtAuthenticationFilter.REQUEST_USER_ATTR);
        if (user == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("error", "Authentication required"));
        }
        if (recipeTitle == null || recipeTitle.isBlank() || title == null || title.isBlank() || content == null || content.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of("error", "recipeTitle, title and content are required"));
        }
        return ResponseEntity.status(HttpStatus.CREATED).body(articleService.create(user, recipeTitle, title, summary, content, tags, image));
    }
}