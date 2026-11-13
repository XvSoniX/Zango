package ir.zango.auth.service;

import ir.zango.auth.config.PasswordResetProperties;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class PasswordResetRateLimiter {

    private final PasswordResetProperties properties;
    private final ConcurrentHashMap<String, Integer> hits = new ConcurrentHashMap<>();
    private final AtomicLong activeWindow = new AtomicLong(Long.MIN_VALUE);

    public PasswordResetRateLimiter(PasswordResetProperties properties) {
        this.properties = properties;
    }

    public boolean allow(String normalizedEmail) {
        long window = Instant.now().toEpochMilli() / properties.getRateLimitWindow().toMillis();
        if (activeWindow.get() != window) {
            synchronized (this) {
                if (activeWindow.get() != window) {
                    hits.clear();
                    activeWindow.set(window);
                }
            }
        }
        int count = hits.merge(hash(normalizedEmail), 1, Integer::sum);
        return count <= properties.getRateLimit();
    }

    private String hash(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is not available", exception);
        }
    }
}
