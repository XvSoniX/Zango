package ir.nextminds.user.dto;

import ir.nextminds.user.entity.User;

import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

public record UserResponse(
        UUID id,
        UUID authUserId,
        String firstName,
        String lastName,
        LocalDate dateOfBirth,
        Instant createdAt,
        Instant updatedAt
) {

    public static UserResponse from(User user) {
        return new UserResponse(
                user.getId(),
                user.getAuthUserId(),
                user.getFirstName(),
                user.getLastName(),
                user.getDateOfBirth(),
                user.getCreatedAt(),
                user.getUpdatedAt()
        );
    }
}
