package ir.nextminds.admin.role.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.util.UUID;

public record AssignRoleRequest(
        @NotNull(message = "{role.id.required}")
        UUID roleId,

        @NotBlank(message = "{reason.required}")
        @Size(max = 500, message = "{reason.size}")
        String reason
) {
}
