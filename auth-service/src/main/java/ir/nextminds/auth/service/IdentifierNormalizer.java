package ir.nextminds.auth.service;

import ir.nextminds.auth.domain.enums.IdentifierTypeEnum;

import java.util.Locale;

public final class IdentifierNormalizer {

    private IdentifierNormalizer() {
    }

    public static String normalize(String identifier, IdentifierTypeEnum identifierType) {
        String normalized = identifier.trim();
        if (identifierType == IdentifierTypeEnum.EMAIL) {
            return normalized.toLowerCase(Locale.ROOT);
        }
        return normalized;
    }
}
