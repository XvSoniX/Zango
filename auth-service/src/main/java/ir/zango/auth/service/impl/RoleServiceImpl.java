package ir.zango.auth.service.impl;

import ir.zango.auth.domain.entity.RoleEntity;
import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.domain.entity.UserRoleEntity;
import ir.zango.auth.domain.entity.UserRoleId;
import ir.zango.auth.dto.AssignRoleRequestDTO;
import ir.zango.auth.dto.CreateRoleRequestDTO;
import ir.zango.auth.dto.CurrentUserRolesResponseDTO;
import ir.zango.auth.dto.RoleResponseDTO;
import ir.zango.auth.dto.UpdateRoleRequestDTO;
import ir.zango.auth.dto.UserRolesResponseDTO;
import ir.zango.auth.exception.DuplicateRoleAssignmentException;
import ir.zango.auth.exception.DuplicateRoleException;
import ir.zango.auth.exception.RoleInUseException;
import ir.zango.auth.exception.RoleNotFoundException;
import ir.zango.auth.exception.UserNotFoundException;
import ir.zango.auth.repository.RoleRepository;
import ir.zango.auth.repository.UserRepository;
import ir.zango.auth.repository.UserRoleRepository;
import ir.zango.auth.service.RoleService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.hibernate.exception.ConstraintViolationException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.SQLException;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class RoleServiceImpl implements RoleService {

    private static final String ROLE_NAME_CONSTRAINT = "uk_roles_name";
    private static final String USER_ROLE_PRIMARY_KEY = "pk_user_roles";

    private final RoleRepository roleRepository;
    private final UserRepository userRepository;
    private final UserRoleRepository userRoleRepository;

    @Override
    @Transactional
    public RoleResponseDTO create(CreateRoleRequestDTO request) {
        String name = request.name().trim();
        if (roleRepository.findByName(name).isPresent()) {
            log.warn("Role creation rejected because {} already exists", name);
            throw new DuplicateRoleException();
        }

        try {
            RoleEntity role = roleRepository.saveAndFlush(
                    RoleEntity.create(name, description(request.description()), Instant.now())
            );
            log.info("Created role {}", role.getName());
            return toResponse(role);
        } catch (DataIntegrityViolationException exception) {
            if (isConstraint(exception, ROLE_NAME_CONSTRAINT)) {
                log.warn("Role creation rejected because {} already exists", name);
                throw new DuplicateRoleException();
            }
            log.error("Role creation failed because of a data integrity violation", exception);
            throw exception;
        }
    }

    @Override
    @Transactional(readOnly = true)
    public List<RoleResponseDTO> findAll() {
        return roleRepository.findAllByOrderByNameAsc().stream()
                .map(this::toResponse)
                .toList();
    }

    @Override
    @Transactional
    public RoleResponseDTO update(UUID roleId, UpdateRoleRequestDTO request) {
        RoleEntity role = roleRepository.findById(roleId).orElseThrow(RoleNotFoundException::new);
        String name = request.name().trim();
        roleRepository.findByName(name)
                .filter(existing -> !existing.getId().equals(roleId))
                .ifPresent(existing -> {
                    log.warn("Role update rejected because {} already exists", name);
                    throw new DuplicateRoleException();
                });
        role.setName(name);
        role.setDescription(description(request.description()));
        log.info("Updated role {}", role.getId());
        return toResponse(role);
    }

    @Override
    @Transactional
    public void delete(UUID roleId) {
        if (!roleRepository.existsById(roleId)) {
            throw new RoleNotFoundException();
        }
        if (userRoleRepository.existsByRole_Id(roleId)) {
            log.warn("Role deletion rejected because role {} is still assigned", roleId);
            throw new RoleInUseException();
        }
        roleRepository.deleteById(roleId);
        log.info("Deleted role {}", roleId);
    }

    @Override
    @Transactional(readOnly = true)
    public CurrentUserRolesResponseDTO findCurrentUserRoles(UUID userId) {
        return new CurrentUserRolesResponseDTO(userRoleRepository.findRoleNamesByUserId(userId));
    }

    @Override
    @Transactional(readOnly = true)
    public UserRolesResponseDTO findUserRoles(UUID userId) {
        if (!userRepository.existsById(userId)) {
            throw new UserNotFoundException();
        }
        return new UserRolesResponseDTO(userId, userRoleRepository.findRoleNamesByUserId(userId));
    }

    @Override
    @Transactional
    public void assign(UUID userId, AssignRoleRequestDTO request) {
        UserEntity user = userRepository.findById(userId).orElseThrow(UserNotFoundException::new);
        RoleEntity role = roleRepository.findById(request.roleId()).orElseThrow(RoleNotFoundException::new);
        UserRoleId id = new UserRoleId(userId, role.getId());
        if (userRoleRepository.existsById(id)) {
            log.warn("Role assignment rejected because user {} already has role {}", userId, role.getName());
            throw new DuplicateRoleAssignmentException();
        }

        try {
            userRoleRepository.saveAndFlush(UserRoleEntity.create(user, role, Instant.now()));
            log.info("Assigned role {} to user {}", role.getName(), userId);
        } catch (DataIntegrityViolationException exception) {
            if (isConstraint(exception, USER_ROLE_PRIMARY_KEY)) {
                log.warn("Role assignment rejected because user {} already has role {}", userId, role.getName());
                throw new DuplicateRoleAssignmentException();
            }
            log.error("Role assignment failed because of a data integrity violation", exception);
            throw exception;
        }
    }

    @Override
    @Transactional
    public void revoke(UUID userId, UUID roleId) {
        if (!userRepository.existsById(userId)) {
            throw new UserNotFoundException();
        }
        if (!roleRepository.existsById(roleId)) {
            throw new RoleNotFoundException();
        }
        UserRoleId id = new UserRoleId(userId, roleId);
        if (!userRoleRepository.existsById(id)) {
            throw new RoleNotFoundException();
        }
        userRoleRepository.deleteById(id);
        log.info("Revoked role {} from user {}", roleId, userId);
    }

    private RoleResponseDTO toResponse(RoleEntity role) {
        return new RoleResponseDTO(role.getId(), role.getName(), role.getDescription());
    }

    private String description(String description) {
        if (description == null || description.isBlank()) {
            return null;
        }
        return description.trim();
    }

    private boolean isConstraint(DataIntegrityViolationException exception, String constraintName) {
        Throwable current = exception;
        while (current != null) {
            if (current instanceof ConstraintViolationException constraintViolation
                    && constraintName.equals(constraintViolation.getConstraintName())) {
                return true;
            }
            if (current instanceof SQLException sqlException
                    && "23505".equals(sqlException.getSQLState())
                    && sqlException.getMessage() != null
                    && sqlException.getMessage().contains(constraintName)) {
                return true;
            }
            current = current.getCause();
        }
        return false;
    }
}
