package ir.nextminds.admin.role.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import io.swagger.v3.oas.annotations.media.Schema;

public record ReasonRequest(
        @Schema(description = "Required business reason for the change / دلیل الزامی تغییر", example = "Access no longer required")
        @NotBlank(message = "{reason.required}")
        @Size(max = 500, message = "{reason.size}")
        String reason
) {
}
