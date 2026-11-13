package ir.zango.auth.dto;

import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;

import java.util.regex.Pattern;

public class IdentifierValidator implements ConstraintValidator<ValidIdentifier, IdentifierDTO> {

    private static final Pattern EMAIL = Pattern.compile("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$");

    @Override
    public boolean isValid(IdentifierDTO request, ConstraintValidatorContext context) {
        if (request == null || request.identifier() == null || request.identifierType() == null) {
            return true;
        }

        String identifier = request.identifier().trim();
        boolean valid = switch (request.identifierType()) {
            case EMAIL -> EMAIL.matcher(identifier).matches();
            case USERNAME -> !identifier.isEmpty() && identifier.chars().noneMatch(Character::isWhitespace);
        };

        if (valid) {
            return true;
        }

        context.disableDefaultConstraintViolation();
        context.buildConstraintViolationWithTemplate("{registration.identifier.invalid}")
                .addPropertyNode("identifier")
                .addConstraintViolation();
        return false;
    }
}
