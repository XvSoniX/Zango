package ir.zango.auth.service;

import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.dto.RefreshTokenResponseDTO;

import java.util.UUID;

public interface RefreshTokenService {

    /**
     * Starts a refresh-token family. Only the SHA-256 hash is stored; the raw token is returned once.
     */
    IssuedRefreshToken issue(UserEntity user);

    /**
     * Exchanges a live refresh token for a new pair and revokes the presented token.
     * Reuse of an already rotated token revokes the rest of that family.
     */
    RefreshTokenResponseDTO rotate(String rawToken);

    /**
     * Revokes the presented refresh token. Unknown and already revoked tokens are ignored.
     */
    void logout(String rawToken);

    /**
     * Revokes every active refresh token belonging to the user.
     */
    void logoutAll(UUID userId);
}
