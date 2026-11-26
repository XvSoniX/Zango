package ir.nextminds.admin.role;

import ir.nextminds.admin.role.dto.CreateRoleRequest;
import ir.nextminds.admin.role.dto.ReasonRequest;
import ir.nextminds.admin.role.dto.RoleResponse;
import ir.nextminds.admin.role.dto.UpdateRoleRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
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
@RequestMapping("/api/v1/admin/roles")
@RequiredArgsConstructor
public class RoleController {

    private final RoleAdministrationService roleAdministrationService;

    @GetMapping
    public List<RoleResponse> list() {
        return roleAdministrationService.listRoles();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public RoleResponse create(@Valid @RequestBody CreateRoleRequest request) {
        return roleAdministrationService.createRole(request);
    }

    @PutMapping("/{roleId}")
    public RoleResponse update(@PathVariable UUID roleId, @Valid @RequestBody UpdateRoleRequest request) {
        return roleAdministrationService.updateRole(roleId, request);
    }

    @DeleteMapping("/{roleId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable UUID roleId, @Valid @RequestBody ReasonRequest request) {
        roleAdministrationService.deleteRole(roleId, request.reason());
    }
}
