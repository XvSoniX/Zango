package ir.zango.auth.dto;

import ir.zango.auth.domain.enums.AccountStatusEnum;
import ir.zango.auth.domain.enums.IdentifierTypeEnum;

import java.util.UUID;

public record RegistrationResponseDTO(
        UUID id,
        String identifier,
        IdentifierTypeEnum identifierType,
        AccountStatusEnum status
) {
}
