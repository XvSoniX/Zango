package ir.zango.auth.service;

import ir.zango.auth.config.PasswordResetProperties;
import ir.zango.auth.domain.entity.CredentialEntity;
import ir.zango.auth.domain.entity.PasswordResetTokenEntity;
import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.domain.enums.AccountStatusEnum;
import ir.zango.auth.domain.enums.IdentifierTypeEnum;
import ir.zango.auth.dto.ChangePasswordRequestDTO;
import ir.zango.auth.dto.ForgotPasswordRequestDTO;
import ir.zango.auth.dto.ResetPasswordRequestDTO;
import ir.zango.auth.exception.AuthenticationFailedException;
import ir.zango.auth.exception.PasswordResetFailedException;
import ir.zango.auth.exception.TooManyRequestsException;
import ir.zango.auth.repository.CredentialRepository;
import ir.zango.auth.repository.PasswordResetTokenRepository;
import ir.zango.auth.service.impl.PasswordServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PasswordServiceTest {

    @Mock
    private CredentialRepository credentialRepository;

    @Mock
    private PasswordResetTokenRepository passwordResetTokenRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private RefreshTokenService refreshTokenService;

    @Mock
    private PasswordResetNotifier passwordResetNotifier;

    @Mock
    private PasswordResetProperties passwordResetProperties;

    @Mock
    private PasswordResetRateLimiter passwordResetRateLimiter;

    @InjectMocks
    private PasswordServiceImpl passwordService;

    @Test
    void changesTheAuthenticatedUsersPasswordAndRevokesRefreshTokens() {
        UUID userId = UUID.randomUUID();
        CredentialEntity credential = credential(userId);
        when(credentialRepository.findByUser_Id(userId)).thenReturn(List.of(credential));
        when(passwordEncoder.matches("current-password", "stored-hash")).thenReturn(true);
        when(passwordEncoder.encode("new-password")).thenReturn("new-hash");

        passwordService.changePassword(userId, new ChangePasswordRequestDTO("current-password", "new-password"));

        assertThat(credential.getPasswordHash()).isEqualTo("new-hash");
        verify(refreshTokenService).logoutAll(userId);
    }

    @Test
    void rejectsAPasswordChangeWhenTheCurrentPasswordDoesNotMatch() {
        UUID userId = UUID.randomUUID();
        when(credentialRepository.findByUser_Id(userId)).thenReturn(List.of(credential(userId)));
        when(passwordEncoder.matches("wrong-password", "stored-hash")).thenReturn(false);

        assertThatThrownBy(() -> passwordService.changePassword(
                userId,
                new ChangePasswordRequestDTO("wrong-password", "new-password")
        )).isInstanceOf(AuthenticationFailedException.class);

        verify(passwordEncoder, never()).encode(any());
        verify(refreshTokenService, never()).logoutAll(any());
    }

    @Test
    void requestsResetWithoutRevealingAMissingEmail() {
        when(passwordResetRateLimiter.allow("missing@example.com")).thenReturn(true);
        when(credentialRepository.findByIdentifierTypeAndIdentifier(IdentifierTypeEnum.EMAIL, "missing@example.com"))
                .thenReturn(Optional.empty());

        passwordService.requestReset(new ForgotPasswordRequestDTO(" Missing@Example.com "));

        verify(passwordResetTokenRepository, never()).saveAndFlush(any());
        verify(passwordResetNotifier, never()).notify(any(), any());
    }

    @Test
    void storesOnlyTheResetTokenHashAndKeepsTheRawTokenOutOfTheResponse() {
        UserEntity user = UserEntity.create(AccountStatusEnum.ACTIVE, Instant.now());
        CredentialEntity credential = CredentialEntity.create(
                user,
                "ada@example.com",
                IdentifierTypeEnum.EMAIL,
                "stored-hash",
                true,
                Instant.now()
        );
        when(passwordResetRateLimiter.allow("ada@example.com")).thenReturn(true);
        when(credentialRepository.findByIdentifierTypeAndIdentifier(IdentifierTypeEnum.EMAIL, "ada@example.com"))
                .thenReturn(Optional.of(credential));
        when(passwordResetProperties.getTtl()).thenReturn(Duration.ofMinutes(30));
        when(passwordResetTokenRepository.saveAndFlush(any())).thenAnswer(invocation -> invocation.getArgument(0));

        passwordService.requestReset(new ForgotPasswordRequestDTO("ada@example.com"));

        ArgumentCaptor<PasswordResetTokenEntity> stored = ArgumentCaptor.forClass(PasswordResetTokenEntity.class);
        ArgumentCaptor<String> rawToken = ArgumentCaptor.forClass(String.class);
        verify(passwordResetTokenRepository).saveAndFlush(stored.capture());
        verify(passwordResetNotifier).notify(eq("ada@example.com"), rawToken.capture());
        assertThat(stored.getValue().getTokenHash()).isEqualTo(sha256(rawToken.getValue()));
        assertThat(stored.getValue().getTokenHash()).isNotEqualTo(rawToken.getValue());
    }

    @Test
    void limitsResetRequestsBeforeLookingUpTheAccount() {
        when(passwordResetRateLimiter.allow("ada@example.com")).thenReturn(false);

        assertThatThrownBy(() -> passwordService.requestReset(new ForgotPasswordRequestDTO("ada@example.com")))
                .isInstanceOf(TooManyRequestsException.class);

        verify(credentialRepository, never()).findByIdentifierTypeAndIdentifier(any(), any());
    }

    @Test
    void rejectsAConsumedResetToken() {
        PasswordResetTokenEntity token = PasswordResetTokenEntity.issue(
                UserEntity.create(AccountStatusEnum.ACTIVE, Instant.now()),
                "hash",
                Instant.now().plusSeconds(60),
                Instant.now()
        );
        token.setUsedAt(Instant.now());
        when(passwordResetTokenRepository.findByTokenHashForUpdate(any())).thenReturn(Optional.of(token));

        assertThatThrownBy(() -> passwordService.resetPassword(new ResetPasswordRequestDTO("raw-token", "new-password")))
                .isInstanceOf(PasswordResetFailedException.class);

        verify(passwordEncoder, never()).encode(any());
        verify(refreshTokenService, never()).logoutAll(any());
    }

    private CredentialEntity credential(UUID userId) {
        UserEntity user = UserEntity.create(AccountStatusEnum.ACTIVE, Instant.now());
        org.springframework.test.util.ReflectionTestUtils.setField(user, "id", userId);
        return CredentialEntity.create(
                user,
                "ada@example.com",
                IdentifierTypeEnum.EMAIL,
                "stored-hash",
                true,
                Instant.now()
        );
    }

    private String sha256(String value) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8))
            );
        } catch (Exception exception) {
            throw new IllegalStateException(exception);
        }
    }
}
