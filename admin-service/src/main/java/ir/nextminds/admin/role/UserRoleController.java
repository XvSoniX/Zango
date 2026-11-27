package ir.nextminds.admin.role;

import ir.nextminds.admin.role.dto.AssignRoleRequest;
import ir.nextminds.admin.role.dto.ReasonRequest;
import ir.nextminds.admin.role.dto.UserRolesResponse;
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
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@Tag(name = "User roles / نقش‌های کاربران", description = "Manage role assignments in Auth. / مدیریت انتساب نقش به کاربران در Auth.")
@SecurityRequirement(name = "bearerAuth")
@ApiResponses({@ApiResponse(responseCode = "400", description = "Invalid request (Problem Detail)"),
        @ApiResponse(responseCode = "401", description = "Missing or invalid token"),
        @ApiResponse(responseCode = "403", description = "ROLE_ADMIN required"),
        @ApiResponse(responseCode = "404", description = "User or role not found"),
        @ApiResponse(responseCode = "409", description = "Assignment conflict or last administrator"),
        @ApiResponse(responseCode = "503", description = "Auth unavailable before sending"),
        @ApiResponse(responseCode = "504", description = "Auth outcome unknown")})
@RequestMapping("/api/v1/admin/users/{userId}/roles")
@RequiredArgsConstructor
public class UserRoleController {

    private final RoleAdministrationService roleAdministrationService;

    @GetMapping
    @Operation(summary = "Get user roles / مشاهده نقش‌های کاربر", description = "Returns the user's ID and assigned role names from Auth. This read does not create an audit record.\n\nشناسه کاربر و نام نقش‌های انتساب‌یافته را از Auth برمی‌گرداند. این درخواست خواندنی Audit ایجاد نمی‌کند.")
    public UserRolesResponse find(@PathVariable UUID userId) {
        return roleAdministrationService.findUserRoles(userId);
    }

    @PostMapping
    @Operation(summary = "Assign a role / انتساب نقش", description = "Assigns an existing role to a user in Auth. The role ID and a nonblank reason are required. Duplicate assignments are rejected and the attempt is audited.\n\nیک نقش موجود را در Auth به کاربر اختصاص می‌دهد. شناسه نقش و دلیل غیرخالی الزامی‌اند. انتساب تکراری رد و تلاش Audit می‌شود.")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void assign(@PathVariable UUID userId, @Valid @RequestBody AssignRoleRequest request) {
        roleAdministrationService.assignRole(userId, request);
    }

    @DeleteMapping("/{roleId}")
    @Operation(summary = "Revoke a role / لغو انتساب نقش", description = "Removes a role assignment in Auth; a nonblank reason is required. Auth rejects revocation of the last active administrator's ROLE_ADMIN assignment. The attempt is audited.\n\nانتساب نقش را در Auth حذف می‌کند؛ دلیل غیرخالی الزامی است. لغو ROLE_ADMIN آخرین مدیر فعال رد و تلاش Audit می‌شود.")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void revoke(
            @PathVariable UUID userId,
            @PathVariable UUID roleId,
            @Valid @RequestBody ReasonRequest request
    ) {
        roleAdministrationService.revokeRole(userId, roleId, request.reason());
    }
}
