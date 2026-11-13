package ir.zango.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ResetPasswordRequestDTO(
        @NotBlank(message = "{password-reset.token.required}")
        @Size(max = 512, message = "{password-reset.token.size}")
        String token,

        @NotBlank(message = "{registration.password.required}")
        @Size(max = 128, message = "{registration.password.size}")
        String newPassword
) {

    @Override
    public String toString() {
        return "ResetPasswordRequestDTO[]";
    }
}
