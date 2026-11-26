package ir.nextminds.admin.role.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ReasonRequest(
        @NotBlank(message = "{reason.required}")
        @Size(max = 500, message = "{reason.size}")
        String reason
) {
}
