package ir.nextminds.auth.security;

import java.time.Instant;

public record AccessToken(
        String value,
        Instant expiresAt,
        long expiresInSeconds
) {
}
