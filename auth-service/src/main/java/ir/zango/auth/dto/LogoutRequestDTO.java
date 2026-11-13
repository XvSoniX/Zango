package ir.zango.auth.dto;

import jakarta.validation.constraints.NotBlank;

public record LogoutRequestDTO(
        @NotBlank(message = "{refresh-token.required}")
        String refreshToken
) {

    @Override
    public String toString() {
        return "LogoutRequestDTO";
    }
}
