package com.example.backend.store;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.stereotype.Component;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

@Component
public class JsonFileStore {
    private final ObjectMapper mapper;
    private final Path dataDir;
    private final Path uploadsDir;

    public JsonFileStore() throws IOException {
        this.mapper = new ObjectMapper();
        this.mapper.registerModule(new JavaTimeModule());
        this.mapper.findAndRegisterModules();
        this.dataDir = Path.of("data");
        this.uploadsDir = dataDir.resolve("uploads");
        Files.createDirectories(dataDir);
        Files.createDirectories(uploadsDir);
    }

    public Path getUploadsDir() {
        return uploadsDir;
    }

    public synchronized <T> List<T> readList(String fileName, TypeReference<List<T>> typeReference) {
        try {
            Path file = dataDir.resolve(fileName);
            if (!Files.exists(file)) {
                return new ArrayList<>();
            }
            return mapper.readValue(file.toFile(), typeReference);
        } catch (Exception e) {
            return new ArrayList<>();
        }
    }

    public synchronized <T> void writeList(String fileName, List<T> data) {
        try {
            Path file = dataDir.resolve(fileName);
            mapper.writerWithDefaultPrettyPrinter().writeValue(file.toFile(), data);
        } catch (IOException e) {
            throw new RuntimeException("Failed to write store file: " + fileName, e);
        }
    }

    public File getDataFile(String fileName) {
        return dataDir.resolve(fileName).toFile();
    }
}