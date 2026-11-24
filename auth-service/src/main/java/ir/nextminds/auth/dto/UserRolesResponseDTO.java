package ir.nextminds.auth.dto;

import java.util.List;
import java.util.UUID;

public record UserRolesResponseDTO(
        UUID userId,
        List<String> roles
) {
}
