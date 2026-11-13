package ir.zango.auth.service.impl;

import ir.zango.auth.config.RefreshTokenProperties;
import ir.zango.auth.domain.entity.RefreshTokenEntity;
import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.dto.RefreshTokenResponseDTO;
import ir.zango.auth.exception.AuthenticationFailedException;
import ir.zango.auth.repository.RefreshTokenRepository;
import ir.zango.auth.security.AccessToken;
import ir.zango.auth.security.JwtAccessTokenGenerator;
import ir.zango.auth.service.AccountStatusRules;
import ir.zango.auth.service.IssuedRefreshToken;
import ir.zango.auth.service.RefreshTokenService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class RefreshTokenServiceImpl implements RefreshTokenService {

    private static final int TOKEN_BYTES = 32;

    private final RefreshTokenRepository refreshTokenRepository;
    private final RefreshTokenProperties refreshTokenProperties;
    private final JwtAccessTokenGenerator jwtAccessTokenGenerator;
    private final SecureRandom secureRandom = new SecureRandom();

    @Override
    @Transactional
    public IssuedRefreshToken issue(UserEntity user) {
        return persist(user, UUID.randomUUID(), Instant.now());
    }

    @Override
    @Transactional(noRollbackFor = AuthenticationFailedException.class)
    public RefreshTokenResponseDTO rotate(String rawToken) {
        RefreshTokenEntity current = refreshTokenRepository
                .findByTokenHashForUpdate(hash(rawToken))
                .orElse(null);
        if (current == null) {
            log.warn("Refresh rejected because the token is unknown");
            throw new AuthenticationFailedException();
        }

        Instant now = Instant.now();
        if (current.getRevokedAt() != null) {
            if (current.getReplacedBy() != null) {
                revokeFamily(current.getFamilyId(), now);
            } else {
                log.warn("Refresh rejected because the token is already revoked");
            }
            throw new AuthenticationFailedException();
        }
        if (!current.getExpiresAt().isAfter(now)) {
            log.warn("Refresh rejected for user {} because the token is expired", current.getUser().getId());
            throw new AuthenticationFailedException();
        }

        UserEntity user = current.getUser();
        if (!AccountStatusRules.canAuthenticate(user)) {
            current.setRevokedAt(now);
            log.warn("Refresh rejected for user {} because the account cannot authenticate", user.getId());
            throw new AuthenticationFailedException();
        }

        IssuedRefreshToken issued = persist(user, current.getFamilyId(), now);
        current.setRevokedAt(now);
        current.setReplacedBy(issued.entity());

        AccessToken accessToken = jwtAccessTokenGenerator.generate(user.getId());
        log.info("Rotated refresh token for user {}", user.getId());
        return new RefreshTokenResponseDTO(
                accessToken.value(),
                issued.value(),
                "Bearer",
                accessToken.expiresAt(),
                accessToken.expiresInSeconds(),
                issued.expiresAt()
        );
    }

    @Override
    @Transactional
    public void logout(String rawToken) {
        RefreshTokenEntity token = refreshTokenRepository.findByTokenHash(hash(rawToken)).orElse(null);
        if (token == null || token.getRevokedAt() != null) {
            log.debug("Logout ignored because the refresh token is unknown or already revoked");
            return;
        }
        token.setRevokedAt(Instant.now());
        log.info("Revoked refresh token for user {}", token.getUser().getId());
    }

    @Override
    @Transactional
    public void logoutAll(UUID userId) {
        refreshTokenRepository.revokeActiveByUserId(userId, Instant.now());
        log.info("Revoked active refresh tokens for user {}", userId);
    }

    private IssuedRefreshToken persist(UserEntity user, UUID familyId, Instant now) {
        String rawToken = rawToken();
        Instant expiresAt = now.plus(refreshTokenProperties.getTtl());
        RefreshTokenEntity entity = refreshTokenRepository.saveAndFlush(
                RefreshTokenEntity.issue(user, hash(rawToken), familyId, expiresAt, now)
        );
        log.debug("Issued refresh token for user {}", user.getId());
        return new IssuedRefreshToken(rawToken, expiresAt, entity);
    }

    /**
     * Revokes the remaining live tokens after a rotated refresh token is presented again.
     */
    private void revokeFamily(UUID familyId, Instant revokedAt) {
        refreshTokenRepository.revokeActiveByFamilyId(familyId, revokedAt);
        log.warn("Rotated refresh token reuse detected; active tokens in the family were revoked");
    }

    private String rawToken() {
        byte[] bytes = new byte[TOKEN_BYTES];
        secureRandom.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String hash(String rawToken) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(rawToken.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException exception) {
            log.error("SHA-256 is not available", exception);
            throw new IllegalStateException("SHA-256 is not available", exception);
        }
    }
}
