package ir.zango.auth.exception;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum AuthErrorCode {

    BAD_REQUEST(
            HttpStatus.BAD_REQUEST,
            "https://zango.ir/problems/bad-request"
    ),

    IDENTIFIER_CONFLICT(
            HttpStatus.CONFLICT,
            "https://zango.ir/problems/identifier-conflict"
    ),

    AUTHENTICATION_FAILED(
            HttpStatus.UNAUTHORIZED,
            "https://zango.ir/problems/authentication-failed"
    ),

    UNAUTHORIZED(
            HttpStatus.UNAUTHORIZED,
            "https://zango.ir/problems/unauthorized"
    ),

    FORBIDDEN(
            HttpStatus.FORBIDDEN,
            "https://zango.ir/problems/forbidden"
    ),

    NOT_FOUND(
            HttpStatus.NOT_FOUND,
            "https://zango.ir/problems/not-found"
    ),

    ROLE_CONFLICT(
            HttpStatus.CONFLICT,
            "https://zango.ir/problems/role-conflict"
    ),

    ROLE_ASSIGNMENT_CONFLICT(
            HttpStatus.CONFLICT,
            "https://zango.ir/problems/role-assignment-conflict"
    ),

    ROLE_IN_USE(
            HttpStatus.CONFLICT,
            "https://zango.ir/problems/role-in-use"
    ),

    PASSWORD_RESET_FAILED(
            HttpStatus.BAD_REQUEST,
            "https://zango.ir/problems/password-reset-failed"
    ),

    TOO_MANY_REQUESTS(
            HttpStatus.TOO_MANY_REQUESTS,
            "https://zango.ir/problems/too-many-requests"
    ),

    INTERNAL_SERVER_ERROR(
            HttpStatus.INTERNAL_SERVER_ERROR,
            "https://zango.ir/problems/internal-server-error"
    );

    private final HttpStatus status;
    private final String type;
}
