package ir.zango.auth.service;

import ir.zango.auth.domain.entity.CredentialEntity;
import ir.zango.auth.domain.entity.RoleEntity;
import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.domain.entity.UserRoleEntity;
import ir.zango.auth.domain.enums.AccountStatusEnum;
import ir.zango.auth.domain.enums.IdentifierTypeEnum;
import ir.zango.auth.dto.RegistrationRequestDTO;
import ir.zango.auth.dto.RegistrationResponseDTO;
import ir.zango.auth.service.impl.RegistrationServiceImpl;
import ir.zango.auth.exception.DuplicateIdentifierException;
import ir.zango.auth.exception.MissingDefaultRoleException;
import ir.zango.auth.repository.CredentialRepository;
import ir.zango.auth.repository.RoleRepository;
import ir.zango.auth.repository.UserRepository;
import ir.zango.auth.repository.UserRoleRepository;
import org.hibernate.exception.ConstraintViolationException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Constructor;
import java.sql.SQLException;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RegistrationServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private CredentialRepository credentialRepository;

    @Mock
    private RoleRepository roleRepository;

    @Mock
    private UserRoleRepository userRoleRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    private RegistrationService registrationService;

    @BeforeEach
    void setUp() {
        registrationService = new RegistrationServiceImpl(
                userRepository,
                credentialRepository,
                roleRepository,
                userRoleRepository,
                passwordEncoder
        );
    }

    @Test
    void registersUserCredentialAndDefaultRole() {
        RegistrationRequestDTO request = new RegistrationRequestDTO(
                "  Ada@Example.com ",
                IdentifierTypeEnum.EMAIL,
                "raw-password"
        );
        RoleEntity role = role();
        when(credentialRepository.findByIdentifierTypeAndIdentifier(IdentifierTypeEnum.EMAIL, "ada@example.com"))
                .thenReturn(Optional.empty());
        when(roleRepository.findByName("ROLE_USER")).thenReturn(Optional.of(role));
        when(passwordEncoder.encode("raw-password")).thenReturn("argon2-hash");
        when(userRepository.saveAndFlush(any(UserEntity.class))).thenAnswer(invocation -> {
            UserEntity user = invocation.getArgument(0);
            ReflectionTestUtils.setField(user, "id", UUID.randomUUID());
            return user;
        });

        RegistrationResponseDTO response = registrationService.register(request);

        ArgumentCaptor<CredentialEntity> credentialCaptor = ArgumentCaptor.forClass(CredentialEntity.class);
        verify(credentialRepository).saveAndFlush(credentialCaptor.capture());
        CredentialEntity credential = credentialCaptor.getValue();

        assertThat(response.id()).isNotNull();
        assertThat(response.identifier()).isEqualTo("ada@example.com");
        assertThat(response.identifierType()).isEqualTo(IdentifierTypeEnum.EMAIL);
        assertThat(response.status()).isEqualTo(AccountStatusEnum.PENDING_VERIFICATION);
        assertThat(credential.getPasswordHash()).isEqualTo("argon2-hash");
        assertThat(credential.getVerified()).isFalse();
        verify(userRoleRepository).saveAndFlush(any(UserRoleEntity.class));
    }

    @Test
    void rejectsAnExistingIdentifierBeforePersistence() {
        RegistrationRequestDTO request = new RegistrationRequestDTO("ada", IdentifierTypeEnum.USERNAME, "raw-password");
        when(credentialRepository.findByIdentifierTypeAndIdentifier(IdentifierTypeEnum.USERNAME, "ada"))
                .thenReturn(Optional.of(CredentialEntity.create(
                        UserEntity.create(AccountStatusEnum.ACTIVE, java.time.Instant.now()),
                        "ada",
                        IdentifierTypeEnum.USERNAME,
                        "existing-hash",
                        false,
                        java.time.Instant.now()
                )));

        assertThatThrownBy(() -> registrationService.register(request))
                .isInstanceOf(DuplicateIdentifierException.class);

        verify(userRepository, never()).saveAndFlush(any());
        verify(passwordEncoder, never()).encode(any());
    }

    @Test
    void failsBeforePersistenceWhenDefaultRoleIsMissing() {
        RegistrationRequestDTO request = new RegistrationRequestDTO("ada", IdentifierTypeEnum.USERNAME, "raw-password");
        when(credentialRepository.findByIdentifierTypeAndIdentifier(IdentifierTypeEnum.USERNAME, "ada"))
                .thenReturn(Optional.empty());
        when(roleRepository.findByName("ROLE_USER")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> registrationService.register(request))
                .isInstanceOf(MissingDefaultRoleException.class);

        verify(userRepository, never()).saveAndFlush(any());
        verify(passwordEncoder, never()).encode(any());
    }

    @Test
    void translatesConcurrentUniqueViolationToDuplicateIdentifier() {
        RegistrationRequestDTO request = new RegistrationRequestDTO("ada", IdentifierTypeEnum.USERNAME, "raw-password");
        when(credentialRepository.findByIdentifierTypeAndIdentifier(IdentifierTypeEnum.USERNAME, "ada"))
                .thenReturn(Optional.empty());
        when(roleRepository.findByName("ROLE_USER")).thenReturn(Optional.of(role()));
        when(passwordEncoder.encode("raw-password")).thenReturn("argon2-hash");
        when(userRepository.saveAndFlush(any(UserEntity.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(credentialRepository.saveAndFlush(any(CredentialEntity.class))).thenThrow(uniqueViolation());

        assertThatThrownBy(() -> registrationService.register(request))
                .isInstanceOf(DuplicateIdentifierException.class);

        verify(userRoleRepository, never()).saveAndFlush(any());
    }

    private RoleEntity role() {
        try {
            Constructor<RoleEntity> constructor = RoleEntity.class.getDeclaredConstructor();
            constructor.setAccessible(true);
            RoleEntity role = constructor.newInstance();
            ReflectionTestUtils.setField(role, "name", "ROLE_USER");
            return role;
        } catch (ReflectiveOperationException exception) {
            throw new IllegalStateException(exception);
        }
    }

    private DataIntegrityViolationException uniqueViolation() {
        SQLException sqlException = new SQLException(
                "duplicate key value violates unique constraint \"uk_credentials_identifier_type_identifier\"",
                "23505"
        );
        return new DataIntegrityViolationException(
                "duplicate",
                new ConstraintViolationException(
                        "duplicate",
                        sqlException,
                        "uk_credentials_identifier_type_identifier"
                )
        );
    }
}
