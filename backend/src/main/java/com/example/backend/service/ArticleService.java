package com.example.backend.service;

import com.example.backend.model.ArticleRecord;
import com.example.backend.security.RequestUser;
import com.example.backend.store.JsonFileStore;
import com.fasterxml.jackson.core.type.TypeReference;
import org.apache.commons.io.FilenameUtils;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class ArticleService {
    private static final String ARTICLES_FILE = "articles.json";
    private final JsonFileStore store;

    public ArticleService(JsonFileStore store) {
        this.store = store;
    }

    public synchronized ArticleRecord create(RequestUser user, String recipeTitle, String title, String summary,
                                             String content, String tagsCsv, MultipartFile image) {
        ArticleRecord article = new ArticleRecord();
        article.setId(UUID.randomUUID().toString());
        article.setRecipeTitle(recipeTitle.trim());
        article.setTitle(title.trim());
        article.setSummary(summary == null ? "" : summary.trim());
        article.setContent(content.trim());
        article.setAuthorId(user.getUserId());
        article.setAuthorName(user.getName());
        article.setTags(parseTags(tagsCsv));
        article.setCreatedAt(Instant.now());
        if (image != null && !image.isEmpty()) {
            saveImage(article, image);
        }
        List<ArticleRecord> all = loadAll();
        all.add(article);
        store.writeList(ARTICLES_FILE, all);
        return article;
    }

    public List<ArticleRecord> listAll() {
        return loadAll().stream()
                .sorted(Comparator.comparing(ArticleRecord::getCreatedAt).reversed())
                .collect(Collectors.toList());
    }

    public List<ArticleRecord> findRelated(String recipeTitle, List<String> alternatives, int limit) {
        String base = normalize(recipeTitle);
        List<String> alt = alternatives == null ? List.of() : alternatives.stream().map(this::normalize).collect(Collectors.toList());
        return listAll().stream()
                .filter(a -> {
                    String rt = normalize(a.getRecipeTitle());
                    String text = normalize(a.getTitle() + " " + a.getSummary() + " " + String.join(" ", a.getTags()));
                    return rt.contains(base) || base.contains(rt) || alt.stream().anyMatch(rt::contains) || text.contains(base);
                })
                .limit(limit)
                .collect(Collectors.toList());
    }

    private List<String> parseTags(String tagsCsv) {
        if (tagsCsv == null || tagsCsv.isBlank()) return new ArrayList<>();
        String[] parts = tagsCsv.split(",");
        List<String> out = new ArrayList<>();
        for (String p : parts) {
            String t = p.trim();
            if (!t.isEmpty()) out.add(t);
        }
        return out;
    }

    private void saveImage(ArticleRecord article, MultipartFile image) {
        try {
            String ext = FilenameUtils.getExtension(image.getOriginalFilename());
            String fileName = article.getId() + (ext == null || ext.isBlank() ? "" : "." + ext);
            Path target = store.getUploadsDir().resolve(fileName);
            Files.copy(image.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);
            article.setImagePath(target.toString());
            article.setImageUrl("/uploads/" + fileName);
        } catch (IOException e) {
            throw new RuntimeException("Failed to store image", e);
        }
    }

    private List<ArticleRecord> loadAll() {
        return store.readList(ARTICLES_FILE, new TypeReference<List<ArticleRecord>>() {});
    }

    private String normalize(String value) {
        return value == null ? "" : value.toLowerCase(Locale.ROOT).trim();
    }
}