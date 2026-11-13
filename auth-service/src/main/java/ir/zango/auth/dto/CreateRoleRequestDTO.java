package ir.zango.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record CreateRoleRequestDTO(
        @NotBlank(message = "{role.name.required}")
        @Size(max = 100, message = "{role.name.size}")
        @Pattern(regexp = "ROLE_[A-Z0-9_]+", message = "{role.name.invalid}")
        String name,

        @Size(max = 255, message = "{role.description.size}")
        String description
) {
}
