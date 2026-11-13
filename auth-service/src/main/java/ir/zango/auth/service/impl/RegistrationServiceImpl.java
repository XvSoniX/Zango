package ir.zango.auth.service.impl;

import ir.zango.auth.domain.entity.CredentialEntity;
import ir.zango.auth.domain.entity.RoleEntity;
import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.domain.entity.UserRoleEntity;
import ir.zango.auth.domain.enums.AccountStatusEnum;
import ir.zango.auth.domain.enums.IdentifierTypeEnum;
import ir.zango.auth.dto.RegistrationRequestDTO;
import ir.zango.auth.dto.RegistrationResponseDTO;
import ir.zango.auth.exception.DuplicateIdentifierException;
import ir.zango.auth.exception.MissingDefaultRoleException;
import ir.zango.auth.repository.CredentialRepository;
import ir.zango.auth.repository.RoleRepository;
import ir.zango.auth.repository.UserRepository;
import ir.zango.auth.repository.UserRoleRepository;
import ir.zango.auth.service.RegistrationService;
import lombok.RequiredArgsConstructor;
import org.hibernate.exception.ConstraintViolationException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.SQLException;
import java.time.Instant;
import java.util.Locale;

@Service
@RequiredArgsConstructor
public class RegistrationServiceImpl implements RegistrationService {

    private static final String DEFAULT_ROLE = "ROLE_USER";
    private static final String IDENTIFIER_UNIQUE_CONSTRAINT = "uk_credentials_identifier_type_identifier";

    private final UserRepository userRepository;
    private final CredentialRepository credentialRepository;
    private final RoleRepository roleRepository;
    private final UserRoleRepository userRoleRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    @Transactional
    public RegistrationResponseDTO register(RegistrationRequestDTO request) {
        IdentifierTypeEnum identifierType = request.identifierType();
        String identifier = normalize(request.identifier(), identifierType);

        if (credentialRepository.findByIdentifierTypeAndIdentifier(identifierType, identifier).isPresent()) {
            throw new DuplicateIdentifierException();
        }

        RoleEntity role = roleRepository.findByName(DEFAULT_ROLE)
                .orElseThrow(MissingDefaultRoleException::new);

        Instant now = Instant.now();
        UserEntity user = userRepository.saveAndFlush(
                UserEntity.create(AccountStatusEnum.PENDING_VERIFICATION, now)
        );

        CredentialEntity credential = CredentialEntity.create(
                user,
                identifier,
                identifierType,
                passwordEncoder.encode(request.password()),
                false,
                now
        );

        try {
            credentialRepository.saveAndFlush(credential);
        } catch (DataIntegrityViolationException exception) {
            if (isDuplicateIdentifier(exception)) {
                throw new DuplicateIdentifierException();
            }
            throw exception;
        }

        userRoleRepository.saveAndFlush(UserRoleEntity.create(user, role, now));

        return new RegistrationResponseDTO(user.getId(), identifier, identifierType, user.getStatus());
    }

    private String normalize(String identifier, IdentifierTypeEnum identifierType) {
        String normalized = identifier.trim();
        if (identifierType == IdentifierTypeEnum.EMAIL) {
            return normalized.toLowerCase(Locale.ROOT);
        }
        return normalized;
    }

    private boolean isDuplicateIdentifier(DataIntegrityViolationException exception) {
        Throwable current = exception;
        while (current != null) {
            if (current instanceof ConstraintViolationException constraintViolation
                    && IDENTIFIER_UNIQUE_CONSTRAINT.equals(constraintViolation.getConstraintName())) {
                return true;
            }
            if (current instanceof SQLException sqlException
                    && "23505".equals(sqlException.getSQLState())
                    && sqlException.getMessage() != null
                    && sqlException.getMessage().contains(IDENTIFIER_UNIQUE_CONSTRAINT)) {
                return true;
            }
            current = current.getCause();
        }
        return false;
    }
}
