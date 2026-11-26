package ir.nextminds.admin.role.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.UUID;

public record AssignRoleRequest(
        @Schema(description = "Existing role UUID / شناسه نقش موجود", example = "6f1c0a3e-7b2d-4e91-9c4a-1d8e5a0b2f11")
        @NotNull(message = "{role.id.required}")
        UUID roleId,

        @Schema(description = "Required business reason for audit / دلیل الزامی برای حسابرسی", example = "Support team membership")
        @NotBlank(message = "{reason.required}")
        @Size(max = 500, message = "{reason.size}")
        String reason
) {
}
