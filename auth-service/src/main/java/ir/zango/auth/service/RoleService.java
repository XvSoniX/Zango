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

    RoleResponseDTO create(CreateRoleRequestDTO request);

    List<RoleResponseDTO> findAll();

    RoleResponseDTO update(UUID roleId, UpdateRoleRequestDTO request);

    void delete(UUID roleId);

    CurrentUserRolesResponseDTO findCurrentUserRoles(UUID userId);

    UserRolesResponseDTO findUserRoles(UUID userId);

    void assign(UUID userId, AssignRoleRequestDTO request);

    void revoke(UUID userId, UUID roleId);
}
