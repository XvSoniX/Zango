package ir.zango.auth.service.impl;

import ir.zango.auth.config.PasswordResetProperties;
import ir.zango.auth.domain.entity.CredentialEntity;
import ir.zango.auth.domain.entity.PasswordResetTokenEntity;
import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.domain.enums.IdentifierTypeEnum;
import ir.zango.auth.dto.ChangePasswordRequestDTO;
import ir.zango.auth.dto.ForgotPasswordRequestDTO;
import ir.zango.auth.dto.ResetPasswordRequestDTO;
import ir.zango.auth.exception.AuthenticationFailedException;
import ir.zango.auth.exception.PasswordResetFailedException;
import ir.zango.auth.exception.TooManyRequestsException;
import ir.zango.auth.repository.CredentialRepository;
import ir.zango.auth.repository.PasswordResetTokenRepository;
import ir.zango.auth.service.AccountStatusRules;
import ir.zango.auth.service.IdentifierNormalizer;
import ir.zango.auth.service.PasswordResetNotifier;
import ir.zango.auth.service.PasswordResetRateLimiter;
import ir.zango.auth.service.PasswordService;
import ir.zango.auth.service.RefreshTokenService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class PasswordServiceImpl implements PasswordService {

    private static final int TOKEN_BYTES = 32;

    private final CredentialRepository credentialRepository;
    private final PasswordResetTokenRepository passwordResetTokenRepository;
    private final PasswordEncoder passwordEncoder;
    private final RefreshTokenService refreshTokenService;
    private final PasswordResetNotifier passwordResetNotifier;
    private final PasswordResetProperties passwordResetProperties;
    private final PasswordResetRateLimiter passwordResetRateLimiter;
    private final SecureRandom secureRandom = new SecureRandom();

    @Override
    @Transactional
    public void changePassword(UUID userId, ChangePasswordRequestDTO request) {
        List<CredentialEntity> credentials = credentialRepository.findByUser_Id(userId);
        if (credentials.isEmpty() || !matchesCurrentPassword(credentials, request.currentPassword())) {
            log.warn("Password change rejected for user {}", userId);
            throw new AuthenticationFailedException();
        }

        Instant now = Instant.now();
        String encoded = passwordEncoder.encode(request.newPassword());
        for (CredentialEntity credential : credentials) {
            credential.assignPasswordHash(encoded);
            credential.assignUpdatedAt(now);
        }
        refreshTokenService.logoutAll(userId);
        log.info("Password changed for user {}", userId);
    }

    @Override
    @Transactional
    public void requestReset(ForgotPasswordRequestDTO request) {
        String email = IdentifierNormalizer.normalize(request.email(), IdentifierTypeEnum.EMAIL);
        if (!passwordResetRateLimiter.allow(email)) {
            log.warn("Password reset request rejected because the rate limit was exceeded");
            throw new TooManyRequestsException();
        }

        CredentialEntity credential = credentialRepository
                .findByIdentifierTypeAndIdentifier(IdentifierTypeEnum.EMAIL, email)
                .orElse(null);
        if (credential == null || !AccountStatusRules.canAuthenticate(credential.getUser())) {
            log.debug("Password reset request ignored");
            return;
        }

        UserEntity user = credential.getUser();
        Instant now = Instant.now();
        passwordResetTokenRepository.consumeActiveByUserId(user.getId(), now);

        String rawToken = rawToken();
        passwordResetTokenRepository.saveAndFlush(PasswordResetTokenEntity.issue(
                user,
                hash(rawToken),
                now.plus(passwordResetProperties.getTtl()),
                now
        ));
        passwordResetNotifier.notify(email, rawToken);
        log.info("Issued password reset token for user {}", user.getId());
    }

    @Override
    @Transactional(noRollbackFor = PasswordResetFailedException.class)
    public void resetPassword(ResetPasswordRequestDTO request) {
        PasswordResetTokenEntity token = passwordResetTokenRepository
                .findByTokenHashForUpdate(hash(request.token()))
                .orElse(null);
        Instant now = Instant.now();
        if (token == null || token.getUsedAt() != null || !token.getExpiresAt().isAfter(now)) {
            log.warn("Password reset rejected because the token is missing, expired, or already used");
            throw new PasswordResetFailedException();
        }

        UserEntity user = token.getUser();
        if (!AccountStatusRules.canAuthenticate(user)) {
            token.setUsedAt(now);
            log.warn("Password reset rejected for user {} because the account cannot authenticate", user.getId());
            throw new PasswordResetFailedException();
        }

        List<CredentialEntity> credentials = credentialRepository.findByUser_Id(user.getId());
        if (credentials.isEmpty()) {
            token.setUsedAt(now);
            log.warn("Password reset rejected for user {} because no credential exists", user.getId());
            throw new PasswordResetFailedException();
        }

        String encoded = passwordEncoder.encode(request.newPassword());
        for (CredentialEntity credential : credentials) {
            credential.assignPasswordHash(encoded);
            credential.assignUpdatedAt(now);
        }
        token.setUsedAt(now);
        passwordResetTokenRepository.consumeActiveByUserIdExcept(user.getId(), token.getId(), now);
        refreshTokenService.logoutAll(user.getId());
        log.info("Password reset completed for user {}", user.getId());
    }

    private boolean matchesCurrentPassword(List<CredentialEntity> credentials, String currentPassword) {
        for (CredentialEntity credential : credentials) {
            if (passwordMatches(currentPassword, credential.getPasswordHash())) {
                return true;
            }
        }
        return false;
    }

    private boolean passwordMatches(String rawPassword, String passwordHash) {
        try {
            return passwordEncoder.matches(rawPassword, passwordHash);
        } catch (IllegalArgumentException exception) {
            log.debug("Stored password hash could not be verified");
            return false;
        }
    }

    private String rawToken() {
        byte[] bytes = new byte[TOKEN_BYTES];
        secureRandom.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String hash(String rawToken) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(rawToken.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException exception) {
            log.error("SHA-256 is not available", exception);
            throw new IllegalStateException("SHA-256 is not available", exception);
        }
    }
}
