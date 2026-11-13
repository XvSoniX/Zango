package ir.zango.auth.exception;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum AuthErrorCode {

    BAD_REQUEST(
            HttpStatus.BAD_REQUEST,
            "http://localhost/problems/bad-request"
    ),

    IDENTIFIER_CONFLICT(
            HttpStatus.CONFLICT,
            "http://localhost/problems/identifier-conflict"
    ),

    AUTHENTICATION_FAILED(
            HttpStatus.UNAUTHORIZED,
            "http://localhost/problems/authentication-failed"
    ),

    UNAUTHORIZED(
            HttpStatus.UNAUTHORIZED,
            "http://localhost/problems/unauthorized"
    ),

    FORBIDDEN(
            HttpStatus.FORBIDDEN,
            "http://localhost/problems/forbidden"
    ),

    NOT_FOUND(
            HttpStatus.NOT_FOUND,
            "http://localhost/problems/not-found"
    ),

    ROLE_CONFLICT(
            HttpStatus.CONFLICT,
            "http://localhost/problems/role-conflict"
    ),

    ROLE_ASSIGNMENT_CONFLICT(
            HttpStatus.CONFLICT,
            "http://localhost/problems/role-assignment-conflict"
    ),

    ROLE_IN_USE(
            HttpStatus.CONFLICT,
            "http://localhost/problems/role-in-use"
    ),

    PASSWORD_RESET_FAILED(
            HttpStatus.BAD_REQUEST,
            "http://localhost/problems/password-reset-failed"
    ),

    TOO_MANY_REQUESTS(
            HttpStatus.TOO_MANY_REQUESTS,
            "http://localhost/problems/too-many-requests"
    ),

    INTERNAL_SERVER_ERROR(
            HttpStatus.INTERNAL_SERVER_ERROR,
            "http://localhost/problems/internal-server-error"
    );

    private final HttpStatus status;
    private final String type;
}
