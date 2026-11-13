package ir.zango.auth.dto;

import java.util.List;

public record CurrentUserRolesResponseDTO(
        List<String> roles
) {
}
