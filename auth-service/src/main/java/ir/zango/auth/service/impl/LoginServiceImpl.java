package ir.zango.auth.service.impl;

import ir.zango.auth.domain.entity.CredentialEntity;
import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.domain.enums.AccountStatusEnum;
import ir.zango.auth.domain.enums.IdentifierTypeEnum;
import ir.zango.auth.dto.LoginRequestDTO;
import ir.zango.auth.dto.LoginResponseDTO;
import ir.zango.auth.exception.AuthenticationFailedException;
import ir.zango.auth.repository.CredentialRepository;
import ir.zango.auth.service.IdentifierNormalizer;
import ir.zango.auth.service.LoginService;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.EnumSet;
import java.util.Set;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class LoginServiceImpl implements LoginService {

    private static final Set<AccountStatusEnum> AUTHENTICATABLE_STATUSES = EnumSet.of(
            AccountStatusEnum.ACTIVE,
            AccountStatusEnum.PENDING_VERIFICATION
    );

    private final CredentialRepository credentialRepository;
    private final PasswordEncoder passwordEncoder;
    private String dummyPasswordHash;

    @PostConstruct
    void initializeDummyPasswordHash() {
        dummyPasswordHash = passwordEncoder.encode(UUID.randomUUID().toString());
    }

    @Override
    @Transactional(readOnly = true)
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

        if (credential == null || !passwordMatches || !canAuthenticate(credential.getUser())) {
            throw new AuthenticationFailedException();
        }

        UserEntity user = credential.getUser();
        return new LoginResponseDTO(
                user.getId(),
                identifier,
                identifierType,
                user.getStatus()
        );
    }

    private boolean canAuthenticate(UserEntity user) {
        return user != null
                && user.getDeletedAt() == null
                && AUTHENTICATABLE_STATUSES.contains(user.getStatus());
    }

    private boolean passwordMatches(String rawPassword, String passwordHash) {
        try {
            return passwordEncoder.matches(rawPassword, passwordHash);
        } catch (IllegalArgumentException exception) {
            return false;
        }
    }
}
