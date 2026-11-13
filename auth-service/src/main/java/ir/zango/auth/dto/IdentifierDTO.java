package ir.zango.auth.dto;

import ir.zango.auth.domain.enums.IdentifierTypeEnum;

public interface IdentifierDTO {

    String identifier();

    IdentifierTypeEnum identifierType();
}
