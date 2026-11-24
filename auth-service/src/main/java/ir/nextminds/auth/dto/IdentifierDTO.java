package ir.nextminds.auth.dto;

import ir.nextminds.auth.domain.enums.IdentifierTypeEnum;

public interface IdentifierDTO {

    String identifier();

    IdentifierTypeEnum identifierType();
}
