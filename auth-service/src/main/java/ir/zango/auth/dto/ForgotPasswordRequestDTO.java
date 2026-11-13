package ir.zango.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record ForgotPasswordRequestDTO(
        @NotBlank(message = "{registration.identifier.required}")
        @Size(max = 255, message = "{registration.identifier.size}")
        @Pattern(regexp = "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$", message = "{registration.identifier.invalid}")
        String email
) {

    @Override
    public String toString() {
        return "ForgotPasswordRequestDTO[]";
    }
}
