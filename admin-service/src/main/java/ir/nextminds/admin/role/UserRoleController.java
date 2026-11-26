package ir.nextminds.admin.role;

import ir.nextminds.admin.role.dto.AssignRoleRequest;
import ir.nextminds.admin.role.dto.ReasonRequest;
import ir.nextminds.admin.role.dto.UserRolesResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/admin/users/{userId}/roles")
@RequiredArgsConstructor
public class UserRoleController {

    private final RoleAdministrationService roleAdministrationService;

    @GetMapping
    public UserRolesResponse find(@PathVariable UUID userId) {
        return roleAdministrationService.findUserRoles(userId);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void assign(@PathVariable UUID userId, @Valid @RequestBody AssignRoleRequest request) {
        roleAdministrationService.assignRole(userId, request);
    }

    @DeleteMapping("/{roleId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void revoke(
            @PathVariable UUID userId,
            @PathVariable UUID roleId,
            @Valid @RequestBody ReasonRequest request
    ) {
        roleAdministrationService.revokeRole(userId, roleId, request.reason());
    }
}
