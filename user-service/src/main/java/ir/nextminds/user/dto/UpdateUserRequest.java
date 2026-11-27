package ir.nextminds.user.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Size;

import java.time.LocalDate;

public record UpdateUserRequest(
        @NotBlank(message = "firstName must not be blank")
        @Size(max = 100, message = "firstName must not exceed 100 characters")
        String firstName,

        @NotBlank(message = "lastName must not be blank")
        @Size(max = 100, message = "lastName must not exceed 100 characters")
        String lastName,

        @NotNull(message = "dateOfBirth is required")
        @Past(message = "dateOfBirth must be in the past")
        LocalDate dateOfBirth
) {
}
