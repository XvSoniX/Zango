package ir.nextminds.admin.role;

import ir.nextminds.admin.role.dto.CreateRoleRequest;
import ir.nextminds.admin.role.dto.ReasonRequest;
import ir.nextminds.admin.role.dto.RoleResponse;
import ir.nextminds.admin.role.dto.UpdateRoleRequest;
import jakarta.validation.Valid;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
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
@Tag(name = "Roles / نقش‌ها", description = "Manage role definitions owned by Auth. / مدیریت تعریف نقش‌ها در سرویس احراز هویت.")
@SecurityRequirement(name = "bearerAuth")
@ApiResponses({@ApiResponse(responseCode = "400", description = "Invalid request (Problem Detail)"),
        @ApiResponse(responseCode = "401", description = "Missing or invalid token"),
        @ApiResponse(responseCode = "403", description = "ROLE_ADMIN required"),
        @ApiResponse(responseCode = "404", description = "Role not found"),
        @ApiResponse(responseCode = "409", description = "Role conflict"),
        @ApiResponse(responseCode = "503", description = "Auth unavailable before sending"),
        @ApiResponse(responseCode = "504", description = "Auth outcome unknown")})
@RequestMapping("/api/v1/admin/roles")
@RequiredArgsConstructor
public class RoleController {

    private final RoleAdministrationService roleAdministrationService;

    @GetMapping
    @Operation(summary = "List roles / فهرست نقش‌ها", description = "Returns the role definitions available in Auth. This read does not create an audit record.\n\nفهرست نقش‌های تعریف‌شده در سرویس احراز هویت را برمی‌گرداند. این درخواست خواندنی رکورد Audit ایجاد نمی‌کند.")
    public List<RoleResponse> list() {
        return roleAdministrationService.listRoles();
    }

    @PostMapping
    @Operation(summary = "Create a role / ایجاد نقش", description = "Creates a uniquely named role in Auth. The optional reason is recorded in an audit attempt before Auth is called. Returns the created role.\n\nیک نقش با نام یکتا در سرویس احراز هویت ایجاد می‌کند. دلیل اختیاری است و پیش از فراخوانی Auth یک رکورد Audit ثبت می‌شود. نقش ایجادشده برگردانده می‌شود.")
    @ResponseStatus(HttpStatus.CREATED)
    public RoleResponse create(@Valid @RequestBody CreateRoleRequest request) {
        return roleAdministrationService.createRole(request);
    }

    @PutMapping("/{roleId}")
    @Operation(summary = "Update a role / ویرایش نقش", description = "Replaces a role's name and description in Auth and audits the attempt. Auth rejects renaming ROLE_ADMIN while an active administrator exists.\n\nنام و توضیح نقش را در Auth جایگزین و تلاش را Audit می‌کند. تغییر نام ROLE_ADMIN در صورت وجود مدیر فعال توسط Auth رد می‌شود.")
    public RoleResponse update(@PathVariable UUID roleId, @Valid @RequestBody UpdateRoleRequest request) {
        return roleAdministrationService.updateRole(roleId, request);
    }

    @DeleteMapping("/{roleId}")
    @Operation(summary = "Delete a role / حذف نقش", description = "Deletes an unassigned role in Auth. A nonblank reason is required and the attempt is audited. Auth rejects deletion when the role is assigned.\n\nیک نقش بدون انتساب را در Auth حذف می‌کند. دلیل غیرخالی الزامی است و تلاش Audit می‌شود. حذف نقش دارای انتساب رد می‌شود.")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable UUID roleId, @Valid @RequestBody ReasonRequest request) {
        roleAdministrationService.deleteRole(roleId, request.reason());
    }
}
