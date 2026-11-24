package ir.nextminds.auth.dto;

import java.util.List;

public record CurrentUserRolesResponseDTO(
        List<String> roles
) {
}
