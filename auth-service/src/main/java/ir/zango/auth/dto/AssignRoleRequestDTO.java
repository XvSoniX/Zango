package ir.zango.auth.dto;

import jakarta.validation.constraints.NotNull;

import java.util.UUID;

public record AssignRoleRequestDTO(
        @NotNull(message = "{role.id.required}")
        UUID roleId
) {
}
