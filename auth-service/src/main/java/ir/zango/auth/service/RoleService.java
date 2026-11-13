package ir.zango.auth.service;

import ir.zango.auth.dto.AssignRoleRequestDTO;
import ir.zango.auth.dto.CreateRoleRequestDTO;
import ir.zango.auth.dto.CurrentUserRolesResponseDTO;
import ir.zango.auth.dto.RoleResponseDTO;
import ir.zango.auth.dto.UpdateRoleRequestDTO;
import ir.zango.auth.dto.UserRolesResponseDTO;

import java.util.List;
import java.util.UUID;

public interface RoleService {

    /**
     * Creates a role. The name must be unique.
     */
    RoleResponseDTO create(CreateRoleRequestDTO request);

    List<RoleResponseDTO> findAll();

    /**
     * Renames a role and replaces its description. The new name must not belong to another role.
     */
    RoleResponseDTO update(UUID roleId, UpdateRoleRequestDTO request);

    /**
     * Deletes a role that is not assigned to any user.
     */
    void delete(UUID roleId);

    CurrentUserRolesResponseDTO findCurrentUserRoles(UUID userId);

    UserRolesResponseDTO findUserRoles(UUID userId);

    /**
     * Assigns a role to a user. A role already held by that user is rejected.
     */
    void assign(UUID userId, AssignRoleRequestDTO request);

    /**
     * Removes one role assignment. The user and the role must both exist.
     */
    void revoke(UUID userId, UUID roleId);
}
