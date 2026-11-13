package ir.zango.auth.dto;

import java.util.List;
import java.util.UUID;

public record UserRolesResponseDTO(
        UUID userId,
        List<String> roles
) {
}
