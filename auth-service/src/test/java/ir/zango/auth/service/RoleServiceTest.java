package ir.zango.auth.service;

import ir.zango.auth.domain.entity.RoleEntity;
import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.domain.entity.UserRoleEntity;
import ir.zango.auth.domain.entity.UserRoleId;
import ir.zango.auth.domain.enums.AccountStatusEnum;
import ir.zango.auth.dto.AssignRoleRequestDTO;
import ir.zango.auth.dto.CreateRoleRequestDTO;
import ir.zango.auth.exception.DuplicateRoleAssignmentException;
import ir.zango.auth.exception.RoleInUseException;
import ir.zango.auth.repository.RoleRepository;
import ir.zango.auth.repository.UserRepository;
import ir.zango.auth.repository.UserRoleRepository;
import ir.zango.auth.service.impl.RoleServiceImpl;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RoleServiceTest {

    @Mock
    private RoleRepository roleRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private UserRoleRepository userRoleRepository;

    @InjectMocks
    private RoleServiceImpl roleService;

    @Test
    void rejectsADuplicateRoleAssignment() {
        UUID userId = UUID.randomUUID();
        UUID roleId = UUID.randomUUID();
        when(userRepository.findById(userId)).thenReturn(Optional.of(
                UserEntity.create(AccountStatusEnum.ACTIVE, Instant.now())
        ));
        when(roleRepository.findById(roleId)).thenReturn(Optional.of(role(roleId, "ROLE_ADMIN")));
        when(userRoleRepository.existsById(new UserRoleId(userId, roleId))).thenReturn(true);

        assertThatThrownBy(() -> roleService.assign(userId, new AssignRoleRequestDTO(roleId)))
                .isInstanceOf(DuplicateRoleAssignmentException.class);

        verify(userRoleRepository, never()).saveAndFlush(any());
    }

    @Test
    void assignsARoleOnceInsideThePersistenceCall() {
        UUID userId = UUID.randomUUID();
        UUID roleId = UUID.randomUUID();
        UserEntity user = UserEntity.create(AccountStatusEnum.ACTIVE, Instant.now());
        RoleEntity role = role(roleId, "ROLE_ADMIN");
        when(userRepository.findById(userId)).thenReturn(Optional.of(user));
        when(roleRepository.findById(roleId)).thenReturn(Optional.of(role));
        when(userRoleRepository.existsById(new UserRoleId(userId, roleId))).thenReturn(false);

        roleService.assign(userId, new AssignRoleRequestDTO(roleId));

        ArgumentCaptor<UserRoleEntity> assignment = ArgumentCaptor.forClass(UserRoleEntity.class);
        verify(userRoleRepository).saveAndFlush(assignment.capture());
        assertThat(assignment.getValue().getUser()).isSameAs(user);
        assertThat(assignment.getValue().getRole()).isSameAs(role);
    }

    @Test
    void refusesToDeleteARoleThatIsStillAssigned() {
        UUID roleId = UUID.randomUUID();
        when(roleRepository.existsById(roleId)).thenReturn(true);
        when(userRoleRepository.existsByRole_Id(roleId)).thenReturn(true);

        assertThatThrownBy(() -> roleService.delete(roleId))
                .isInstanceOf(RoleInUseException.class);

        verify(roleRepository, never()).deleteById(roleId);
    }

    @Test
    void storesANewRoleByItsDatabaseName() {
        when(roleRepository.findByName("ROLE_SUPPORT")).thenReturn(Optional.empty());
        when(roleRepository.saveAndFlush(any(RoleEntity.class))).thenAnswer(invocation -> invocation.getArgument(0));

        var response = roleService.create(new CreateRoleRequestDTO("ROLE_SUPPORT", " Support "));

        assertThat(response.name()).isEqualTo("ROLE_SUPPORT");
        assertThat(response.description()).isEqualTo("Support");
    }

    private RoleEntity role(UUID id, String name) {
        RoleEntity role = RoleEntity.create(name, null, Instant.now());
        ReflectionTestUtils.setField(role, "id", id);
        return role;
    }
}
