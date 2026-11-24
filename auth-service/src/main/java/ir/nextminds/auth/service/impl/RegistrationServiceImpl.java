package ir.nextminds.auth.service.impl;

import ir.nextminds.auth.domain.entity.CredentialEntity;
import ir.nextminds.auth.domain.entity.RoleEntity;
import ir.nextminds.auth.domain.entity.UserEntity;
import ir.nextminds.auth.domain.entity.UserRoleEntity;
import ir.nextminds.auth.domain.enums.AccountStatusEnum;
import ir.nextminds.auth.domain.enums.IdentifierTypeEnum;
import ir.nextminds.auth.dto.RegistrationRequestDTO;
import ir.nextminds.auth.dto.RegistrationResponseDTO;
import ir.nextminds.auth.exception.DuplicateIdentifierException;
import ir.nextminds.auth.exception.MissingDefaultRoleException;
import ir.nextminds.auth.repository.CredentialRepository;
import ir.nextminds.auth.repository.RoleRepository;
import ir.nextminds.auth.repository.UserRepository;
import ir.nextminds.auth.repository.UserRoleRepository;
import ir.nextminds.auth.service.IdentifierNormalizer;
import ir.nextminds.auth.service.RegistrationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.hibernate.exception.ConstraintViolationException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.SQLException;
import java.time.Instant;

@Service
@RequiredArgsConstructor
@Slf4j
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
        String identifier = IdentifierNormalizer.normalize(request.identifier(), identifierType);

        if (credentialRepository.findByIdentifierTypeAndIdentifier(identifierType, identifier).isPresent()) {
            log.warn("Registration rejected because the {} identifier is already in use", identifierType);
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
                log.warn("Registration rejected because the {} identifier is already in use", identifierType);
                throw new DuplicateIdentifierException();
            }
            log.error("Registration failed because of a data integrity violation", exception);
            throw exception;
        }

        userRoleRepository.saveAndFlush(UserRoleEntity.create(user, role, now));
        log.info("Registered user {} with identifier type {}", user.getId(), identifierType);

        return new RegistrationResponseDTO(user.getId(), identifier, identifierType, user.getStatus());
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
