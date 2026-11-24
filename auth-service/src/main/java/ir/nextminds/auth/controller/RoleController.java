package ir.nextminds.auth.controller;

import ir.nextminds.auth.dto.AssignRoleRequestDTO;
import ir.nextminds.auth.dto.CreateRoleRequestDTO;
import ir.nextminds.auth.dto.CurrentUserRolesResponseDTO;
import ir.nextminds.auth.dto.RoleResponseDTO;
import ir.nextminds.auth.dto.UpdateRoleRequestDTO;
import ir.nextminds.auth.dto.UserRolesResponseDTO;
import ir.nextminds.auth.exception.AuthenticationFailedException;
import ir.nextminds.auth.service.RoleService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class RoleController {

    private final RoleService roleService;

    @GetMapping("/roles/me")
    public CurrentUserRolesResponseDTO currentRoles(@AuthenticationPrincipal Jwt jwt) {
        return roleService.findCurrentUserRoles(subject(jwt));
    }

    @GetMapping("/admin/roles")
    public List<RoleResponseDTO> findAll() {
        return roleService.findAll();
    }

    @PostMapping("/admin/roles")
    @ResponseStatus(HttpStatus.CREATED)
    public RoleResponseDTO create(@Valid @RequestBody CreateRoleRequestDTO request) {
        return roleService.create(request);
    }

    @PutMapping("/admin/roles/{roleId}")
    public RoleResponseDTO update(
            @PathVariable UUID roleId,
            @Valid @RequestBody UpdateRoleRequestDTO request
    ) {
        return roleService.update(roleId, request);
    }

    @DeleteMapping("/admin/roles/{roleId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable UUID roleId) {
        roleService.delete(roleId);
    }

    @GetMapping("/admin/users/{userId}/roles")
    public UserRolesResponseDTO userRoles(@PathVariable UUID userId) {
        return roleService.findUserRoles(userId);
    }

    @PostMapping("/admin/users/{userId}/roles")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void assign(@PathVariable UUID userId, @Valid @RequestBody AssignRoleRequestDTO request) {
        roleService.assign(userId, request);
    }

    @DeleteMapping("/admin/users/{userId}/roles/{roleId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void revoke(@PathVariable UUID userId, @PathVariable UUID roleId) {
        roleService.revoke(userId, roleId);
    }

    private UUID subject(Jwt jwt) {
        if (jwt == null || jwt.getSubject() == null) {
            throw new AuthenticationFailedException();
        }
        try {
            return UUID.fromString(jwt.getSubject());
        } catch (IllegalArgumentException exception) {
            throw new AuthenticationFailedException();
        }
    }
}
