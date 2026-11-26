package ir.nextminds.admin.role.dto;

import java.util.List;
import java.util.UUID;

public record UserRolesResponse(
        UUID userId,
        List<String> roles
) {
}
