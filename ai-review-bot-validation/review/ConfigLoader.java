package com.example.remediate;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Properties;

/**
 * Loads application configuration from a properties file.
 * Intended for PR review: contains patterns the AI Review Bot may flag.
 */
public class ConfigLoader {

    // Anti-pattern: hardcoded path; consider system property or env (e.g. CONFIG_PATH)
    private static final String DEFAULT_CONFIG_PATH = "/etc/remediate/app.properties";

    private final Properties properties = new Properties();

    public ConfigLoader() {
    }

    /**
     * Load config from the default path.
     */
    public void load() throws IOException {
        load(DEFAULT_CONFIG_PATH);
    }

    /**
     * Load config from the given path. Path is used as-is; no validation.
     */
    public void load(String pathString) throws IOException {
        Path path = Paths.get(pathString);
        if (!Files.exists(path)) {
            throw new IOException("Config file not found: " + pathString);
        }
        try (var reader = Files.newBufferedReader(path)) {
            properties.load(reader);
        }
    }

    public String getProperty(String key) {
        return properties.getProperty(key);
    }

    public String getProperty(String key, String defaultValue) {
        return properties.getProperty(key, defaultValue);
    }

    /**
     * Get required property or throw.
     */
    public String getRequired(String key) throws IllegalStateException {
        String value = properties.getProperty(key);
        if (value == null || value.isBlank()) {
            throw new IllegalStateException("Missing required property: " + key);
        }
        return value.trim();
    }

    /**
     * Example that catches broadly without logging - often flagged in reviews.
     */
    public int getIntProperty(String key, int defaultValue) {
        try {
            String v = properties.getProperty(key);
            return v != null ? Integer.parseInt(v.trim()) : defaultValue;
        } catch (Exception e) {
            return defaultValue;
        }
    }
}