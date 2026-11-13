package ir.zango.auth.dto;

import ir.zango.auth.domain.enums.AccountStatusEnum;
import ir.zango.auth.domain.enums.IdentifierTypeEnum;

import java.time.Instant;
import java.util.UUID;

public record LoginResponseDTO(
        UUID id,
        String identifier,
        IdentifierTypeEnum identifierType,
        AccountStatusEnum status,
        String accessToken,
        String tokenType,
        Instant expiresAt,
        long expiresIn
) {
}
