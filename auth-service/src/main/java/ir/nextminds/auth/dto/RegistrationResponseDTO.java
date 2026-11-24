package ir.nextminds.auth.dto;

import ir.nextminds.auth.domain.enums.AccountStatusEnum;
import ir.nextminds.auth.domain.enums.IdentifierTypeEnum;

import java.util.UUID;

public record RegistrationResponseDTO(
        UUID id,
        String identifier,
        IdentifierTypeEnum identifierType,
        AccountStatusEnum status
) {
}
