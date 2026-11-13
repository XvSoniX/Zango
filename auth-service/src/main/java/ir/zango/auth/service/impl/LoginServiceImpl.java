package ir.zango.auth.service.impl;

import ir.zango.auth.domain.entity.CredentialEntity;
import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.domain.enums.IdentifierTypeEnum;
import ir.zango.auth.dto.LoginRequestDTO;
import ir.zango.auth.dto.LoginResponseDTO;
import ir.zango.auth.exception.AuthenticationFailedException;
import ir.zango.auth.repository.CredentialRepository;
import ir.zango.auth.security.AccessToken;
import ir.zango.auth.security.JwtAccessTokenGenerator;
import ir.zango.auth.service.AccountStatusRules;
import ir.zango.auth.service.IdentifierNormalizer;
import ir.zango.auth.service.IssuedRefreshToken;
import ir.zango.auth.service.LoginService;
import ir.zango.auth.service.RefreshTokenService;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class LoginServiceImpl implements LoginService {

    private final CredentialRepository credentialRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtAccessTokenGenerator jwtAccessTokenGenerator;
    private final RefreshTokenService refreshTokenService;
    private String dummyPasswordHash;

    @PostConstruct
    void initializeDummyPasswordHash() {
        dummyPasswordHash = passwordEncoder.encode(UUID.randomUUID().toString());
    }

    @Override
    @Transactional
    public LoginResponseDTO login(LoginRequestDTO request) {
        IdentifierTypeEnum identifierType = request.identifierType();
        String identifier = IdentifierNormalizer.normalize(request.identifier(), identifierType);
        CredentialEntity credential = credentialRepository
                .findByIdentifierTypeAndIdentifier(identifierType, identifier)
                .orElse(null);

        String passwordHash = credential == null
                ? dummyPasswordHash
                : credential.getPasswordHash();

        boolean passwordMatches = passwordMatches(request.password(), passwordHash);

        if (credential == null || !passwordMatches || !AccountStatusRules.canAuthenticate(credential.getUser())) {
            throw new AuthenticationFailedException();
        }

        UserEntity user = credential.getUser();
        AccessToken accessToken = jwtAccessTokenGenerator.generate(user.getId());
        IssuedRefreshToken refreshToken = refreshTokenService.issue(user);
        return new LoginResponseDTO(
                user.getId(),
                identifier,
                identifierType,
                user.getStatus(),
                accessToken.value(),
                "Bearer",
                accessToken.expiresAt(),
                accessToken.expiresInSeconds(),
                refreshToken.value(),
                refreshToken.expiresAt()
        );
    }

    private boolean passwordMatches(String rawPassword, String passwordHash) {
        try {
            return passwordEncoder.matches(rawPassword, passwordHash);
        } catch (IllegalArgumentException exception) {
            return false;
        }
    }
}
