package ir.zango.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ChangePasswordRequestDTO(
        @NotBlank(message = "{registration.password.required}")
        @Size(max = 128, message = "{registration.password.size}")
        String currentPassword,

        @NotBlank(message = "{registration.password.required}")
        @Size(max = 128, message = "{registration.password.size}")
        String newPassword
) {

    @Override
    public String toString() {
        return "ChangePasswordRequestDTO[]";
    }
}
