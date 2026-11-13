package ir.zango.auth.dto;

import java.time.Instant;

public record RefreshTokenResponseDTO(
        String accessToken,
        String refreshToken,
        String tokenType,
        Instant expiresAt,
        long expiresIn,
        Instant refreshExpiresAt
) {

    @Override
    public String toString() {
        return "RefreshTokenResponseDTO[tokenType=" + tokenType + ", expiresAt=" + expiresAt + "]";
    }
}
