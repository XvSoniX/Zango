package ir.zango.auth.dto;

import ir.zango.auth.domain.enums.IdentifierTypeEnum;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

@ValidIdentifier
public record LoginRequestDTO(
        @NotBlank(message = "{registration.identifier.required}")
        @Size(max = 255, message = "{registration.identifier.size}")
        String identifier,

        @NotNull(message = "{registration.identifier-type.required}")
        IdentifierTypeEnum identifierType,

        @NotBlank(message = "{registration.password.required}")
        @Size(max = 128, message = "{registration.password.size}")
        String password
) implements IdentifierDTO {

    @Override
    public String toString() {
        return "LoginRequestDTO[identifierType=" + identifierType + "]";
    }
}
