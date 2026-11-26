package ir.nextminds.admin.role.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import io.swagger.v3.oas.annotations.media.Schema;

public record UpdateRoleRequest(
        @Schema(description = "Replacement role name / نام جدید نقش", example = "ROLE_SUPPORT")
        @NotBlank(message = "{role.name.required}")
        @Size(max = 100, message = "{role.name.size}")
        @Pattern(regexp = "ROLE_[A-Z0-9_]+", message = "{role.name.invalid}")
        String name,

        @Schema(description = "Replacement description; null clears it / توضیح جدید؛ null آن را پاک می‌کند")
        @Size(max = 255, message = "{role.description.size}")
        String description,

        @Schema(description = "Optional audit reason / دلیل اختیاری برای حسابرسی")
        @Size(max = 500, message = "{reason.size}")
        String reason
) {
}
