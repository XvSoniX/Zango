package ir.nextminds.admin.role.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import io.swagger.v3.oas.annotations.media.Schema;

public record CreateRoleRequest(
        @Schema(description = "Unique role name, starting with ROLE_ / نام یکتای نقش با پیشوند ROLE_", example = "ROLE_SUPPORT")
        @NotBlank(message = "{role.name.required}")
        @Size(max = 100, message = "{role.name.size}")
        @Pattern(regexp = "ROLE_[A-Z0-9_]+", message = "{role.name.invalid}")
        String name,

        @Schema(description = "Optional role description / توضیح اختیاری نقش", example = "Support team")
        @Size(max = 255, message = "{role.description.size}")
        String description,

        @Schema(description = "Optional audit reason / دلیل اختیاری برای حسابرسی", example = "Support access")
        @Size(max = 500, message = "{reason.size}")
        String reason
) {
}
