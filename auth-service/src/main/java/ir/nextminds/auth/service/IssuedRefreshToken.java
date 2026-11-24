package ir.nextminds.auth.service;

import ir.nextminds.auth.domain.entity.RefreshTokenEntity;

import java.time.Instant;

public record IssuedRefreshToken(String value, Instant expiresAt, RefreshTokenEntity entity) {

    @Override
    public String toString() {
        return "IssuedRefreshToken[expiresAt=" + expiresAt + "]";
    }
}
